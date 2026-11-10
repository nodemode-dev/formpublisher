#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod files;
mod reveal;

use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicI32, AtomicU16, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::DialogExt;

const DEFAULT_PORT: u16 = 8280;
const ENGINE_WAIT: Duration = Duration::from_secs(60);
const ENGINE_NAME: &str = if cfg!(windows) { "formpublisher-engine.exe" } else { "formpublisher-engine" };
const FALLBACK_SIZE: (f64, f64) = (1280.0, 800.0);
const MIN_SIZE: (f64, f64) = (1024.0, 680.0);
const SCREEN_FRACTION: f64 = 0.9;

struct Backend(Mutex<Option<Child>>);

static PORT: AtomicU16 = AtomicU16::new(DEFAULT_PORT);

static ENGINE_GROUP: AtomicI32 = AtomicI32::new(0);

#[cfg(unix)]
extern "C" {
    fn signal(signum: i32, handler: usize) -> usize;
    fn kill(pid: i32, sig: i32) -> i32;
    fn _exit(code: i32) -> !;
}

#[cfg(unix)]
extern "C" fn on_signal(_: i32) {
    let group = ENGINE_GROUP.load(Ordering::SeqCst);
    unsafe {
        if group > 0 {
            kill(-group, 15);
        }
        _exit(0)
    }
}

#[cfg(unix)]
fn watch_signals() {
    for number in [1, 2, 15] {
        unsafe {
            signal(number, on_signal as *const () as usize);
        }
    }
}

fn engine_addr() -> String {
    format!("127.0.0.1:{}", PORT.load(Ordering::SeqCst))
}

fn engine_url() -> String {
    format!("http://{}", engine_addr())
}

fn choose_port() -> u16 {
    if let Some(port) = std::env::var("FORMPUBLISHER_PORT").ok().and_then(|raw| raw.trim().parse::<u16>().ok()).filter(|p| *p > 0) {
        return port;
    }
    let free = |port: u16| TcpListener::bind(("127.0.0.1", port)).is_ok();
    if free(DEFAULT_PORT) {
        return DEFAULT_PORT;
    }
    TcpListener::bind(("127.0.0.1", 0))
        .and_then(|listener| listener.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(DEFAULT_PORT)
}

fn healthy() -> bool {
    let address = engine_addr();
    let Ok(addr) = address.parse::<SocketAddr>() else { return false };
    let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(400)) else { return false };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(800)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(800)));
    let request = format!("GET /api/health HTTP/1.1\r\nHost: {address}\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut head = [0u8; 16];
    let Ok(read) = stream.read(&mut head) else { return false };
    String::from_utf8_lossy(&head[..read]).contains(" 200")
}

fn sidecar_path() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let program = exe.parent()?.join(ENGINE_NAME);
    program.is_file().then_some(program)
}

fn source_root() -> Option<PathBuf> {
    let root = std::env::var_os("FORMPUBLISHER_ROOT")
        .map(PathBuf::from)
        .or_else(|| cfg!(debug_assertions).then(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..")))?;
    root.join("formpublisher").is_file().then_some(root)
}

fn spawn_engine() -> Option<Child> {
    let mut command = if let Some(program) = sidecar_path() {
        Command::new(program)
    } else {
        let root = source_root()?;
        let mut command = Command::new(root.join("formpublisher"));
        command.arg("serve").current_dir(root);
        command
    };
    command
        .env("FORMPUBLISHER_PORT", PORT.load(Ordering::SeqCst).to_string())
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    command.spawn().ok()
}

fn kill_backend(handle: &tauri::AppHandle) {
    let child = handle.state::<Backend>().0.lock().ok().and_then(|mut slot| slot.take());
    let Some(mut child) = child else { return };
    #[cfg(unix)]
    {
        let pid = format!("-{}", child.id());
        let signal = |sig: &str| {
            Command::new("kill")
                .args([sig, "--", pid.as_str()])
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status()
                .is_ok_and(|s| s.success())
        };
        if signal("-TERM") {
            for _ in 0..30 {
                std::thread::sleep(Duration::from_millis(50));
                if matches!(child.try_wait(), Ok(Some(_))) {
                    return;
                }
            }
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}

fn focus_main(handle: &tauri::AppHandle) {
    if let Some(window) = handle.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn open_main(handle: &tauri::AppHandle) {
    let (width, height) = handle
        .primary_monitor()
        .ok()
        .flatten()
        .map(|monitor| {
            let logical = monitor.size().to_logical::<f64>(monitor.scale_factor());
            (
                (logical.width * SCREEN_FRACTION).max(MIN_SIZE.0),
                (logical.height * SCREEN_FRACTION).max(MIN_SIZE.1),
            )
        })
        .unwrap_or(FALLBACK_SIZE);
    let Ok(url) = engine_url().parse() else { return };
    let builder = WebviewWindowBuilder::new(handle, "main", WebviewUrl::External(url))
        .title("FormPublisher")
        .visible(reveal::BUILD_VISIBLE)
        .background_color(reveal::BACKGROUND)
        .inner_size(width, height)
        .min_inner_size(MIN_SIZE.0, MIN_SIZE.1)
        .center()
        .disable_drag_drop_handler();
    #[cfg(target_os = "macos")]
    let builder = builder.title_bar_style(tauri::TitleBarStyle::Overlay).hidden_title(true);
    match builder.build() {
        Ok(window) => reveal::conceal(&window),
        Err(_) => reveal::close_splash(handle),
    }
}

fn engine_failed(handle: &tauri::AppHandle) {
    reveal::close_splash(handle);
    let _ = handle
        .dialog()
        .message("The FormPublisher engine did not start. Please relaunch the app.")
        .blocking_show();
    kill_backend(handle);
    handle.exit(1);
}

fn start_engine(handle: tauri::AppHandle) {
    std::thread::spawn(move || {
        if !healthy() {
            match spawn_engine() {
                Some(child) => {
                    ENGINE_GROUP.store(child.id() as i32, Ordering::SeqCst);
                    if let Ok(mut slot) = handle.state::<Backend>().0.lock() {
                        *slot = Some(child);
                    }
                }
                None => {
                    engine_failed(&handle);
                    return;
                }
            }
            let started = Instant::now();
            while !healthy() {
                if started.elapsed() > ENGINE_WAIT {
                    engine_failed(&handle);
                    return;
                }
                std::thread::sleep(Duration::from_millis(250));
            }
        }
        let opener = handle.clone();
        let _ = handle.run_on_main_thread(move || open_main(&opener));
    });
}

#[tauri::command(async)]
fn open_window(app: tauri::AppHandle, path: String, title: Option<String>) -> Result<(), String> {
    let relative = path.trim_start_matches('/');
    let url = format!("{}/{relative}", engine_url()).parse().map_err(|_| "bad path".to_string())?;
    let label = format!(
        "extra-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis())
            .unwrap_or(0)
    );
    let window = WebviewWindowBuilder::new(&app, label, WebviewUrl::External(url))
        .title(title.unwrap_or_else(|| "FormPublisher".to_string()))
        .visible(reveal::BUILD_VISIBLE)
        .background_color(reveal::BACKGROUND)
        .inner_size(MIN_SIZE.0, MIN_SIZE.1)
        .min_inner_size(MIN_SIZE.0, MIN_SIZE.1)
        .center()
        .disable_drag_drop_handler()
        .build()
        .map_err(|e| e.to_string())?;
    reveal::conceal_extra(&window);
    Ok(())
}

fn main() {
    reveal::mark_launch();
    #[cfg(unix)]
    watch_signals();
    PORT.store(choose_port(), Ordering::SeqCst);
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| focus_main(app)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Backend(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![reveal::app_ready, open_window, files::reveal_path])
        .setup(|app| {
            let handle = app.handle().clone();
            reveal::round_splash(&handle);
            start_engine(handle);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building the FormPublisher app");

    app.run(|handle, event| {
        match event {
            RunEvent::WindowEvent { event: tauri::WindowEvent::Destroyed, .. } if handle.webview_windows().is_empty() => handle.exit(0),
            RunEvent::Exit => kill_backend(handle),
            _ => {}
        }
    });
}
