@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set "PYBIN=py -3.12") || (set "PYBIN=python")
where npm >nul 2>nul || ( echo [formpublisher] Node.js 22.12 or newer is needed & exit /b 1 )
echo [formpublisher] engine: backend\venv
if not exist backend\venv\Scripts\python.exe %PYBIN% -m venv backend\venv
if errorlevel 1 ( echo [formpublisher] Python 3.12 is needed & exit /b 1 )
backend\venv\Scripts\python.exe -m pip install -q --upgrade pip
backend\venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
if errorlevel 1 exit /b 1
echo [formpublisher] interface: frontend\node_modules
pushd frontend
call npm ci --no-audit --no-fund
popd
echo [formpublisher] done. Start with formpublisher.bat (then open http://localhost:5280); formpublisher.bat agents install connects Claude Code, Codex and Cursor
