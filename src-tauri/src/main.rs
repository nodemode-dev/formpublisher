#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod engine_start;
mod files;
mod reveal;
mod traffic_lights;
#[cfg(windows)]
mod win_job;

use std::io::{BufRead, BufReader, Read};
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicI32, AtomicU16, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use engine_start::{Failure, Tail};
use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::DialogExt;

const DEFAULT_PORT: u16 = 8280;
const ENGINE_NAME: &str = if cfg!(windows) { "formpublisher-engine.exe" } else { "formpublisher-engine" };
const ENGINE_FOLDER: &str = "engine";
const FALLBACK_SIZE: (f64, f64) = (1280.0, 800.0);
const MIN_SIZE: (f64, f64) = (1024.0, 680.0);
const SCREEN_FRACTION: f64 = 0.9;

struct Backend(Mutex<Option<Child>>);

struct EngineTail(Arc<Mutex<Tail>>);

struct WindowKey(Arc<Mutex<Option<String>>>);

fn key_script(handle: &tauri::AppHandle) -> String {
    let key = handle.state::<WindowKey>().0.lock().ok().and_then(|slot| slot.clone()).unwrap_or_default();
    engine_start::key_script(&engine_url(), &key)
}

fn grant_engine_origin(handle: &tauri::AppHandle) -> bool {
    let port = PORT.load(Ordering::SeqCst);
    if port == DEFAULT_PORT {
        return true;
    }
    let mut capability = tauri::ipc::CapabilityBuilder::new("engine-origin")
        .remote(format!("http://127.0.0.1:{port}/*"))
        .local(false)
        .windows(["main", "extra-*"]);
    for permission in engine_start::WINDOW_PERMISSIONS {
        capability = capability.permission(*permission);
    }
    handle.add_capability(capability).is_ok()
}

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

fn engine_program(handle: &tauri::AppHandle) -> Option<PathBuf> {
    let exe_dir = std::env::current_exe().ok().and_then(|exe| exe.parent().map(PathBuf::from));
    let mut places: Vec<PathBuf> = Vec::new();
    if let Ok(resources) = handle.path().resource_dir() {
        places.push(resources.join(ENGINE_FOLDER));
    }
    if let Some(dir) = exe_dir {
        places.push(dir.join("../Resources").join(ENGINE_FOLDER));
        places.push(dir.join(ENGINE_FOLDER));
        places.push(dir);
    }
    places.into_iter().map(|folder| folder.join(ENGINE_NAME)).find(|program| program.is_file())
}

fn source_root() -> Option<PathBuf> {
    let root = std::env::var_os("FORMPUBLISHER_ROOT")
        .map(PathBuf::from)
        .or_else(|| cfg!(debug_assertions).then(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..")))?;
    root.join("formpublisher").is_file().then_some(root)
}

fn follow<R: Read + Send + 'static>(stream: Option<R>, tail: Arc<Mutex<Tail>>, key: Arc<Mutex<Option<String>>>) {
    let Some(stream) = stream else { return };
    std::thread::spawn(move || {
        for line in BufReader::new(stream).lines() {
            let Ok(line) = line else { break };
            if let Some(found) = engine_start::window_key(&line) {
                if let Ok(mut slot) = key.lock() {
                    *slot = Some(found);
                }
                continue;
            }
            if let Ok(mut kept) = tail.lock() {
                kept.push(&line);
            }
        }
    });
}

fn spawn_engine(handle: &tauri::AppHandle) -> Result<Child, Failure> {
    let mut command = if let Some(program) = engine_program(handle) {
        Command::new(program)
    } else {
        let root = source_root().ok_or(Failure::Missing)?;
        let mut command = Command::new(root.join("formpublisher"));
        command.arg("serve").current_dir(root);
        command
    };
    command
        .env("FORMPUBLISHER_PORT", PORT.load(Ordering::SeqCst).to_string())
        .env(engine_start::SHELL_ENV, std::process::id().to_string())
        .env(engine_start::DESKTOP_ENV, "1")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
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
    let mut child = command.spawn().map_err(|err| Failure::NotStarted(err.to_string()))?;
    #[cfg(windows)]
    win_job::hold_pid(child.id());
    let tail = handle.state::<EngineTail>().0.clone();
    let key = handle.state::<WindowKey>().0.clone();
    follow(child.stdout.take(), tail.clone(), key.clone());
    follow(child.stderr.take(), tail, key);
    Ok(child)
}

fn kill_backend(handle: &tauri::AppHandle) {
    let child = handle.state::<Backend>().0.lock().ok().and_then(|mut slot| slot.take());
    #[cfg(windows)]
    win_job::end();
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
        .initialization_script(key_script(handle))
        .visible(reveal::BUILD_VISIBLE)
        .background_color(reveal::BACKGROUND)
        .inner_size(width, height)
        .min_inner_size(MIN_SIZE.0, MIN_SIZE.1)
        .center()
        .disable_drag_drop_handler();
    #[cfg(target_os = "macos")]
    let builder = builder.title_bar_style(tauri::TitleBarStyle::Overlay).hidden_title(true);
    let builder = builder.on_page_load(|window, payload| {
        if matches!(payload.event(), tauri::webview::PageLoadEvent::Finished) {
            traffic_lights::place(&window.as_ref().window());
        }
    });
    match builder.build() {
        Ok(window) => {
            reveal::conceal(&window);
            traffic_lights::place(&window.as_ref().window());
        }
        Err(_) => {
            let failed = handle.clone();
            std::thread::spawn(move || engine_failed(&failed, Failure::Window));
        }
    }
}

fn engine_failed(handle: &tauri::AppHandle, failure: Failure) {
    reveal::close_splash(handle);
    std::thread::sleep(Duration::from_millis(150));
    let tail = handle.state::<EngineTail>().0.lock().map(|kept| kept.lines()).unwrap_or_default();
    let log = engine_start::engine_log().filter(|path| path.is_file());
    let _ = handle
        .dialog()
        .message(engine_start::message(&failure, &tail, log.as_deref()))
        .title("FormPublisher")
        .kind(tauri_plugin_dialog::MessageDialogKind::Error)
        .blocking_show();
    kill_backend(handle);
    handle.exit(1);
}

fn engine_exit(handle: &tauri::AppHandle) -> Option<Option<i32>> {
    let backend = handle.state::<Backend>();
    let mut slot = backend.0.lock().ok()?;
    let child = slot.as_mut()?;
    match child.try_wait() {
        Ok(Some(status)) => Some(status.code()),
        _ => None,
    }
}

fn start_engine(handle: tauri::AppHandle) {
    std::thread::spawn(move || {
        engine_start::replace_leftover();
        PORT.store(choose_port(), Ordering::SeqCst);
        match spawn_engine(&handle) {
            Ok(child) => {
                ENGINE_GROUP.store(child.id() as i32, Ordering::SeqCst);
                if let Ok(mut slot) = handle.state::<Backend>().0.lock() {
                    *slot = Some(child);
                }
            }
            Err(failure) => {
                engine_failed(&handle, failure);
                return;
            }
        }
        let started = Instant::now();
        let own = env!("CARGO_PKG_VERSION");
        loop {
            if let Some(answer) = engine_start::health(PORT.load(Ordering::SeqCst)) {
                if answer.app == "formpublisher" && answer.version == own {
                    break;
                }
                engine_failed(&handle, Failure::WrongVersion(answer.version));
                return;
            }
            if let Some(code) = engine_exit(&handle) {
                engine_failed(&handle, Failure::Stopped(code));
                return;
            }
            if started.elapsed() > engine_start::HEALTH_WAIT {
                engine_failed(&handle, Failure::TimedOut);
                return;
            }
            std::thread::sleep(Duration::from_millis(250));
        }
        let asked = Instant::now();
        while handle.state::<WindowKey>().0.lock().map(|slot| slot.is_none()).unwrap_or(true) {
            if asked.elapsed() > engine_start::KEY_WAIT {
                engine_failed(&handle, Failure::NoKey);
                return;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        if !grant_engine_origin(&handle) {
            engine_failed(&handle, Failure::Window);
            return;
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
    let builder = WebviewWindowBuilder::new(&app, label, WebviewUrl::External(url))
        .title(title.unwrap_or_else(|| "FormPublisher".to_string()))
        .initialization_script(key_script(&app))
        .visible(reveal::BUILD_VISIBLE)
        .background_color(reveal::BACKGROUND)
        .inner_size(MIN_SIZE.0, MIN_SIZE.1)
        .min_inner_size(MIN_SIZE.0, MIN_SIZE.1)
        .center()
        .disable_drag_drop_handler();
    #[cfg(target_os = "macos")]
    let builder = builder.title_bar_style(tauri::TitleBarStyle::Overlay).hidden_title(true);
    let window = builder
        .on_page_load(|window, payload| {
            if matches!(payload.event(), tauri::webview::PageLoadEvent::Finished) {
                traffic_lights::place(&window.as_ref().window());
            }
        })
        .build()
        .map_err(|e| e.to_string())?;
    reveal::conceal_extra(&window);
    traffic_lights::place(&window.as_ref().window());
    Ok(())
}

fn main() {
    reveal::mark_launch();
    #[cfg(unix)]
    watch_signals();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| focus_main(app)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Backend(Mutex::new(None)))
        .manage(EngineTail(Arc::new(Mutex::new(Tail::default()))))
        .manage(WindowKey(Arc::new(Mutex::new(None))))
        .on_window_event(|window, event| {
            if window.label() != "splash"
                && matches!(
                    event,
                    tauri::WindowEvent::Resized(_)
                        | tauri::WindowEvent::Focused(_)
                        | tauri::WindowEvent::ThemeChanged(_)
                        | tauri::WindowEvent::ScaleFactorChanged { .. }
                )
            {
                traffic_lights::place(window);
            }
        })
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
