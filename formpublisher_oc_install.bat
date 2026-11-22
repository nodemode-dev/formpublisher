@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set "PYBIN=py -3.12") || (set "PYBIN=python")
where npm >nul 2>nul || ( echo [formpublisher] Node.js 22.12 or newer is needed & exit /b 1 )
node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a>22||(a===22&&b>=12)?0:1)" || ( echo [formpublisher] Node.js 22.12 or newer is needed & exit /b 1 )
echo [formpublisher] engine: backend\venv
if not exist backend\venv\Scripts\python.exe %PYBIN% -m venv backend\venv
if errorlevel 1 ( echo [formpublisher] Python 3.12 is needed & exit /b 1 )
backend\venv\Scripts\python.exe -m pip install -q --require-hashes -r backend\requirements.lock
if errorlevel 1 exit /b 1
echo [formpublisher] deep checks: Playwright is installed; no browser is downloaded; deep checks use a Chrome or Edge you already have
where cargo >nul 2>nul
if errorlevel 1 (
  echo [formpublisher] Rust is not installed, so .fweb projects cannot be opened yet. Get Rust from https://rustup.rs, then run setup\install_compiler.bat
) else (
  echo [formpublisher] compiler: backend\bin\formweb-core.exe
  call setup\install_compiler.bat
  if errorlevel 1 ( echo [formpublisher] the core build failed ^(see above^) & exit /b 1 )
)
echo [formpublisher] interface: frontend\node_modules
pushd frontend
call npm ci --no-audit --no-fund
popd
echo [formpublisher] done. Start with formpublisher.bat (then open http://localhost:5280); formpublisher.bat agents install connects Claude Code, Codex and Cursor
