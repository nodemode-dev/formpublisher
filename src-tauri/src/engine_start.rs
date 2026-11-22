use std::collections::VecDeque;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

pub const APP: &str = "FormPublisher";
pub const SHELL_ENV: &str = "FORMPUBLISHER_SHELL_PID";
pub const DESKTOP_ENV: &str = "FORMPUBLISHER_DESKTOP";
pub const HEALTH_WAIT: Duration = Duration::from_secs(90);
pub const BUSY_CODE: i32 = 2;
const HOME_ENV: &str = "FORMPUBLISHER_HOME";
const HOME_NAME: &str = "FormPublisher";
const ENGINE_FILE: &str = "engine.json";
const LOG_FOLDER: &str = "logs";
const LOG_NAME: &str = "engine.log";
const KEY_MARK: &str = "window-key";
const TAIL_LINES: usize = 12;
const LINE_CHARS: usize = 300;
const LEFTOVER_WAIT: Duration = Duration::from_secs(5);
const BODY_LIMIT: u64 = 65_536;
pub const KEY_WAIT: Duration = Duration::from_secs(10);
const KEY_LINE: &str = "formpublisher-window-key: ";
const KEY_MIN: usize = 32;
pub const WINDOW_PERMISSIONS: &[&str] = &[
    "core:default",
    "core:window:allow-set-title",
    "core:window:allow-close",
    "core:window:allow-minimize",
    "core:window:allow-toggle-maximize",
    "core:window:allow-start-dragging",
    "shell:allow-open",
    "dialog:allow-open",
    "dialog:allow-save",
    "dialog:allow-message",
    "dialog:allow-ask",
    "allow-app-ready",
    "allow-open-window",
    "allow-reveal-path",
];

pub fn window_key(line: &str) -> Option<String> {
    let value = line.trim().strip_prefix(KEY_LINE)?.trim();
    let sound = value.len() >= KEY_MIN && value.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-');
    sound.then(|| value.to_string())
}

pub fn key_script(origin: &str, key: &str) -> String {
    if key.is_empty() {
        return String::new();
    }
    format!("if (window.location.origin === {origin:?} && window.top === window) {{ window.__FORMPUBLISHER_WINDOW_KEY = {key:?}; }}")
}

#[derive(Debug, PartialEq)]
pub enum Failure {
    Missing,
    NoKey,
    NotStarted(String),
    Stopped(Option<i32>),
    TimedOut,
    WrongVersion(String),
    Window,
}

#[derive(Default)]
pub struct Tail(VecDeque<String>);

impl Tail {
    pub fn push(&mut self, line: &str) {
        if line.contains(KEY_MARK) {
            return;
        }
        let clean: String = line.chars().filter(|c| !c.is_control()).take(LINE_CHARS).collect();
        if clean.trim().is_empty() {
            return;
        }
        if self.0.len() == TAIL_LINES {
            self.0.pop_front();
        }
        self.0.push_back(clean);
    }

    pub fn lines(&self) -> Vec<String> {
        self.0.iter().cloned().collect()
    }
}

pub fn sentence(failure: &Failure) -> String {
    match failure {
        Failure::Missing => format!("{APP} could not start: its engine program is missing from the install. Installing {APP} again puts it back."),
        Failure::NotStarted(reason) => format!("{APP} could not start its engine: {reason}"),
        Failure::Stopped(Some(BUSY_CODE)) => format!("{APP} could not start: another copy of its engine holds its data folder."),
        Failure::Stopped(Some(code)) => format!("{APP} could not start: its engine stopped with code {code} before the window could open."),
        Failure::Stopped(None) => format!("{APP} could not start: its engine stopped before the window could open."),
        Failure::TimedOut => format!("{APP} could not start: it waited {} seconds for its engine to answer and that did not happen.", HEALTH_WAIT.as_secs()),
        Failure::WrongVersion(found) => format!("{APP} could not start: the engine that answered is version {found}, not this app's {}.", env!("CARGO_PKG_VERSION")),
        Failure::NoKey => format!("{APP} could not start: it waited {} seconds for its engine to hand over the key for the window and that did not happen.", KEY_WAIT.as_secs()),
        Failure::Window => format!("{APP} could not open its window."),
    }
}

pub fn message(failure: &Failure, tail: &[String], log: Option<&Path>) -> String {
    let mut text = sentence(failure);
    if !tail.is_empty() {
        text.push_str("\n\nThe engine's last lines:\n");
        text.push_str(&tail.join("\n"));
    } else if matches!(failure, Failure::Stopped(_) | Failure::TimedOut) {
        text.push_str("\n\nThe engine wrote nothing before that.");
    }
    if let Some(path) = log {
        text.push_str("\n\nThe engine's log: ");
        text.push_str(&path.to_string_lossy());
    }
    text
}

fn user_home() -> Option<PathBuf> {
    let name = if cfg!(windows) { "USERPROFILE" } else { "HOME" };
    std::env::var(name).ok().filter(|value| !value.is_empty()).map(PathBuf::from)
}

pub fn data_folder() -> Option<PathBuf> {
    let home = user_home();
    if let Some(raw) = std::env::var(HOME_ENV).ok().map(|value| value.trim().to_string()).filter(|value| !value.is_empty()) {
        return match (raw.strip_prefix('~'), home) {
            (Some(rest), Some(home)) if rest.is_empty() || rest.starts_with('/') || rest.starts_with('\\') => {
                Some(home.join(rest.trim_start_matches(['/', '\\'])))
            }
            _ => Some(PathBuf::from(raw)),
        };
    }
    home.map(|home| home.join(HOME_NAME))
}

pub fn engine_log() -> Option<PathBuf> {
    data_folder().map(|folder| folder.join(LOG_FOLDER).join(LOG_NAME))
}

pub struct Health {
    pub app: String,
    pub version: String,
}

pub fn health(port: u16) -> Option<Health> {
    let address = format!("127.0.0.1:{port}");
    let addr = address.parse::<SocketAddr>().ok()?;
    let mut stream = TcpStream::connect_timeout(&addr, Duration::from_millis(400)).ok()?;
    let _ = stream.set_read_timeout(Some(Duration::from_millis(1500)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(800)));
    let request = format!("GET /api/health HTTP/1.1\r\nHost: {address}\r\nConnection: close\r\n\r\n");
    stream.write_all(request.as_bytes()).ok()?;
    let mut raw = Vec::new();
    stream.take(BODY_LIMIT).read_to_end(&mut raw).ok()?;
    let text = String::from_utf8_lossy(&raw);
    let (head, body) = text.split_once("\r\n\r\n")?;
    if !head.lines().next()?.contains(" 200") {
        return None;
    }
    let start = body.find('{')?;
    let end = body.rfind('}')?;
    let value: serde_json::Value = serde_json::from_str(body.get(start..=end)?).ok()?;
    Some(Health {
        app: value.get("app")?.as_str()?.to_string(),
        version: value.get("version")?.as_str()?.to_string(),
    })
}

struct Announced {
    pid: u32,
    port: u16,
}

fn announced() -> Option<Announced> {
    let text = std::fs::read_to_string(data_folder()?.join(ENGINE_FILE)).ok()?;
    let value: serde_json::Value = serde_json::from_str(&text).ok()?;
    if value.get("app")?.as_str()? != "formpublisher" {
        return None;
    }
    let pid = u32::try_from(value.get("pid")?.as_u64()?).ok().filter(|pid| *pid > 1)?;
    let port = u16::try_from(value.get("port")?.as_u64()?).ok().filter(|port| *port > 0)?;
    Some(Announced { pid, port })
}

fn quiet(mut command: Command) -> bool {
    command.stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    command.status().is_ok_and(|status| status.success())
}

fn end_pid(pid: u32, hard: bool) -> bool {
    if cfg!(windows) {
        let mut command = Command::new("taskkill");
        command.args(["/PID", &pid.to_string(), "/T", "/F"]);
        quiet(command)
    } else {
        let mut command = Command::new("kill");
        command.args([if hard { "-KILL" } else { "-TERM" }, &pid.to_string()]);
        quiet(command)
    }
}

pub fn replace_leftover() -> Option<String> {
    let found = announced()?;
    if found.pid == std::process::id() {
        return None;
    }
    let answer = health(found.port).filter(|answer| answer.app == "formpublisher")?;
    end_pid(found.pid, false);
    let started = Instant::now();
    let mut forced = false;
    while health(found.port).is_some() {
        if started.elapsed() > LEFTOVER_WAIT {
            break;
        }
        if !forced && started.elapsed() > LEFTOVER_WAIT / 2 {
            forced = true;
            end_pid(found.pid, true);
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    Some(answer.version)
}
