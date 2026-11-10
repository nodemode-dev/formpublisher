@echo off
setlocal
cd /d "%~dp0"
set "LOG=%~dp0build_app.log"
echo [formpublisher] build_app.bat: the FormPublisher desktop build, start to finish > "%LOG%"
call :step "checking the tools"
where node >nul 2>nul || ( call :die "Node 22.12 or newer is required" & exit /b 1 )
where npm >nul 2>nul || ( call :die "Node 22.12 or newer is required" & exit /b 1 )
where cargo >nul 2>nul || ( call :die "Rust is required: install it from https://rustup.rs" & exit /b 1 )
where bash >nul 2>nul || ( call :die "Git for Windows is required (its bash freezes the engine): https://git-scm.com/download/win" & exit /b 1 )
where py >nul 2>nul || where python >nul 2>nul || ( call :die "Python 3.12 or newer is required" & exit /b 1 )
call :step "installing the engine and the window"
if not exist backend\venv\Scripts\python.exe call formpublisher_oc_install.bat >> "%LOG%" 2>&1
if not exist frontend\node_modules ( pushd frontend & call npm ci --no-audit --no-fund >> "%LOG%" 2>&1 & popd )
call :step "building the window"
pushd frontend
call npm run build >> "%LOG%" 2>&1
if errorlevel 1 ( popd & call :die "the interface build failed" & exit /b 1 )
popd
call :step "freezing the engine into the app's sidecar"
bash setup/freeze_backend >> "%LOG%" 2>&1
if errorlevel 1 ( call :die "the engine freeze failed" & exit /b 1 )
call :step "building the desktop app (the first build compiles several hundred Rust crates)"
call npx --yes @tauri-apps/cli@2 build >> "%LOG%" 2>&1
if errorlevel 1 ( call :die "tauri build failed" & exit /b 1 )
echo [formpublisher] done. The installer is in src-tauri\target\release\bundle
echo [formpublisher] done. The installer is in src-tauri\target\release\bundle >> "%LOG%"
exit /b 0
:step
echo.
echo [formpublisher] == %~1
echo [formpublisher] == %~1 >> "%LOG%"
exit /b 0
:die
echo [formpublisher] error: %~1
echo [formpublisher] error: %~1 >> "%LOG%"
echo [formpublisher] the full log is %LOG%
exit /b 1
