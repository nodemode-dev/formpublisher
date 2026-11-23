@echo off
setlocal
cd /d "%~dp0"
set "CMD=%~1"
if "%CMD%"=="" set "CMD=boot"
call :rest %*
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
if /i "%CMD%"=="run" ( "%PYEXE%" backend\formpublisher_engine.py cli %REST% & goto :eof )
if /i "%CMD%"=="cli" ( "%PYEXE%" backend\formpublisher_engine.py cli %REST% & goto :eof )
if /i "%CMD%"=="mcp" ( "%PYEXE%" backend\formpublisher_engine.py mcp %REST% & goto :eof )
if /i "%CMD%"=="agents" ( "%PYEXE%" setup\agents.py %REST% & goto :eof )
if /i "%CMD%"=="vendor" ( "%PYEXE%" setup\vendor_check.py %REST% & goto :eof )
if /i "%CMD%"=="doctor" goto doctor
if /i "%CMD%"=="test" ( call setup\test.bat %REST% & goto :eof )
if /i "%CMD%"=="version" ( "%PYEXE%" backend\formpublisher_engine.py --version & goto :eof )
if /i "%CMD%"=="help" goto usage
echo [formpublisher] unknown command: %CMD%
goto usage
:boot
if not exist frontend\node_modules ( call formpublisher_oc_install.bat & if errorlevel 1 exit /b 1 )
if not exist backend\venv\Scripts\python.exe ( call formpublisher_oc_install.bat & if errorlevel 1 exit /b 1 )
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
if /i "%~2"=="build" ( call build_app.bat & goto :eof ) else if not exist frontend\node_modules\.bin\tauri.cmd ( echo [formpublisher] the desktop tools are missing: run formpublisher.bat install & exit /b 1 )
start "formpublisher engine" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --host %FORMPUBLISHER_HOST% --port %FORMPUBLISHER_PORT%"
start "formpublisher interface" cmd /k "cd /d %~dp0frontend && node node_modules\vite\bin\vite.js"
frontend\node_modules\.bin\tauri.cmd dev --no-dev-server-wait
goto :eof
:doctor
echo   node       & node -v 2>nul || echo missing
echo   python     & "%PYEXE%" -V
echo   claude     & where claude 2>nul || echo missing
echo   cargo      & cargo -V 2>nul || echo missing (desktop builds only)
set "VLINE=the check did not run"
for /f "usebackq delims=" %%L in (`""%PYEXE%" setup\vendor_check.py --check 2^>^&1 ^| findstr /v /c:"not a git checkout""`) do call :vfirst "%%L"
set "VTAIL="
if not "%VLINE:~0,15%"=="vendor: in step" set "VTAIL= (formpublisher.bat vendor --check lists them all)"
echo   vendor     %VLINE%%VTAIL%
goto :eof
:vfirst
if not defined VLINE_SET set "VLINE=%~1" & set "VLINE_SET=1"
goto :eof
:rest
set "REST="
:rest_next
shift
if "%~1"=="" exit /b 0
set REST=%REST% %1
goto rest_next
:usage
echo formpublisher.bat [command]
echo   boot ^| install ^| backend ^| frontend ^| build ^| serve ^| desktop dev ^| desktop build
echo   run ... ^| mcp ... ^| agents install^|status^|sync ^| vendor --check ^| doctor ^| version ^| help
exit /b 0
