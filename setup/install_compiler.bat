@echo off
setlocal
cd /d "%~dp0..\vendor\formweb-native"
if errorlevel 1 ( echo [formpublisher] vendor\formweb-native is missing & exit /b 1 )
set "PYEXE=python"
if exist "%~dp0..\backend\venv\Scripts\python.exe" set "PYEXE=%~dp0..\backend\venv\Scripts\python.exe"
"%PYEXE%" "%~dp0vendor_check.py" --check
if errorlevel 1 ( echo [formpublisher] the vendored crates are out of step ^(see above^); nothing was built & exit /b 1 )
where cargo >nul 2>nul || ( echo [formpublisher] cargo is missing. Install Rust stable from https://rustup.rs and run setup\install_compiler.bat again & exit /b 1 )
echo [formpublisher] building formweb-core (the first build takes a few minutes)
cargo build --release --locked -p formweb-core
if errorlevel 1 exit /b 1
if not exist "%~dp0..\backend\bin" mkdir "%~dp0..\backend\bin"
copy /y target\release\formweb-core.exe "%~dp0..\backend\bin\formweb-core.exe" >nul
if errorlevel 1 exit /b 1
echo [formpublisher] formweb-core ready: backend\bin\formweb-core.exe
