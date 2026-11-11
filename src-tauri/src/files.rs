use std::path::{Path, PathBuf};
use std::process::Command;

fn data_folder() -> Result<PathBuf, String> {
    let configured = std::env::var("FORMPUBLISHER_HOME").unwrap_or_default();
    let configured = configured.trim();
    let base = if configured.is_empty() {
        let user = std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" })
            .map(PathBuf::from)
            .ok_or_else(|| "The data folder is not known".to_string())?;
        user.join("FormPublisher")
    } else if let Some(rest) = configured.strip_prefix("~/") {
        let user = std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" })
            .map(PathBuf::from)
            .ok_or_else(|| "The data folder is not known".to_string())?;
        user.join(rest)
    } else {
        PathBuf::from(configured)
    };
    base.canonicalize().map_err(|_| "The data folder does not exist yet".to_string())
}

fn plain(path: PathBuf) -> PathBuf {
    #[cfg(windows)]
    {
        if let Some(rest) = path.to_str().and_then(|s| s.strip_prefix(r"\\?\")) {
            return PathBuf::from(rest);
        }
    }
    path
}

fn checked(raw: &str) -> Result<PathBuf, String> {
    if raw.trim().is_empty() {
        return Err("No path was given".to_string());
    }
    let home = data_folder()?;
    let target = Path::new(raw).canonicalize().map_err(|_| "That path does not exist".to_string())?;
    if !target.starts_with(&home) {
        return Err("Only paths inside the FormPublisher data folder can be shown".to_string());
    }
    Ok(plain(target))
}

#[tauri::command(async)]
pub fn reveal_path(path: String) -> Result<(), String> {
    let target = checked(&path)?;
    let mut command;
    #[cfg(target_os = "macos")]
    {
        command = Command::new("open");
        command.arg("-R").arg(&target);
    }
    #[cfg(windows)]
    {
        command = Command::new("explorer");
        let mut select = std::ffi::OsString::from("/select,");
        select.push(&target);
        command.arg(select);
    }
    #[cfg(not(any(target_os = "macos", windows)))]
    {
        let folder = if target.is_dir() { target.clone() } else { target.parent().map(Path::to_path_buf).unwrap_or(target.clone()) };
        command = Command::new("xdg-open");
        command.arg(folder);
    }
    command.spawn().map(|_| ()).map_err(|e| format!("The file manager did not open: {e}"))
}
