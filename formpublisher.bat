@echo off
setlocal
cd /d "%~dp0"
set "CMD=%~1"
if "%CMD%"=="" set "CMD=boot"
set "PYEXE=python"
if exist backend\venv\Scripts\python.exe set "PYEXE=backend\venv\Scripts\python.exe"
if "%FORMPUBLISHER_HOST%"=="" set "FORMPUBLISHER_HOST=127.0.0.1"
if "%FORMPUBLISHER_PORT%"=="" set "FORMPUBLISHER_PORT=8280"
if /i "%CMD%"=="boot" goto boot
if /i "%CMD%"=="dev" goto boot
if /i "%CMD%"=="install" ( call formpublisher_oc_install.bat & goto :eof )
if /i "%CMD%"=="backend" goto backend
if /i "%CMD%"=="frontend" goto frontend
if /i "%CMD%"=="build" goto build
if /i "%CMD%"=="serve" goto serve
if /i "%CMD%"=="desktop" goto desktop
if /i "%CMD%"=="run" ( shift & "%PYEXE%" backend\formpublisher_engine.py cli %1 %2 %3 %4 %5 %6 %7 %8 %9 & goto :eof )
if /i "%CMD%"=="cli" ( shift & "%PYEXE%" backend\formpublisher_engine.py cli %1 %2 %3 %4 %5 %6 %7 %8 %9 & goto :eof )
if /i "%CMD%"=="mcp" ( shift & "%PYEXE%" backend\formpublisher_engine.py mcp %1 %2 %3 %4 %5 %6 %7 %8 %9 & goto :eof )
if /i "%CMD%"=="agents" ( shift & "%PYEXE%" setup\agents.py %1 %2 %3 %4 %5 %6 %7 %8 %9 & goto :eof )
if /i "%CMD%"=="vendor" ( shift & "%PYEXE%" setup\vendor_check.py %1 %2 %3 %4 %5 %6 %7 %8 %9 & goto :eof )
if /i "%CMD%"=="doctor" goto doctor
if /i "%CMD%"=="version" ( "%PYEXE%" backend\formpublisher_engine.py --version & goto :eof )
if /i "%CMD%"=="help" goto usage
echo [formpublisher] unknown command: %CMD%
goto usage
:boot
if not exist frontend\node_modules call formpublisher_oc_install.bat
if not exist backend\venv\Scripts\python.exe call formpublisher_oc_install.bat
start "formpublisher engine" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --host %FORMPUBLISHER_HOST% --port %FORMPUBLISHER_PORT%"
start "formpublisher interface" cmd /k "cd /d %~dp0frontend && node node_modules\vite\bin\vite.js"
echo [formpublisher] open http://localhost:5280
goto :eof
:backend
cd backend
venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --host %FORMPUBLISHER_HOST% --port %FORMPUBLISHER_PORT%
goto :eof
:frontend
cd frontend
node node_modules\vite\bin\vite.js
goto :eof
:build
cd frontend
call npm run build
goto :eof
:serve
if not exist frontend\dist\index.html ( pushd frontend & call npm run build & popd )
echo [formpublisher] open http://%FORMPUBLISHER_HOST%:%FORMPUBLISHER_PORT%
cd backend
venv\Scripts\python.exe -m uvicorn app.main:app --host %FORMPUBLISHER_HOST% --port %FORMPUBLISHER_PORT%
goto :eof
:desktop
if /i "%~2"=="build" ( call build_app.bat & goto :eof )
start "formpublisher engine" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --host %FORMPUBLISHER_HOST% --port %FORMPUBLISHER_PORT%"
start "formpublisher interface" cmd /k "cd /d %~dp0frontend && node node_modules\vite\bin\vite.js"
frontend\node_modules\.bin\tauri.cmd dev --no-dev-server-wait
goto :eof
:doctor
echo   node       & node -v
echo   python     & "%PYEXE%" -V
echo   claude     & where claude 2>nul || echo missing
echo   cargo      & cargo -V 2>nul || echo missing (desktop builds only)
goto :eof
:usage
echo formpublisher.bat [command]
echo   boot ^| install ^| backend ^| frontend ^| build ^| serve ^| desktop dev ^| desktop build
echo   run ... ^| mcp ... ^| agents install^|status^|sync ^| vendor --check ^| doctor ^| version ^| help
exit /b 0
