@echo off
setlocal
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo [formpublisher] creating the backend venv
  py -3.12 -m venv venv
  venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
if "%FORMPUBLISHER_HOST%"=="" set "FORMPUBLISHER_HOST=127.0.0.1"
if "%FORMPUBLISHER_PORT%"=="" set "FORMPUBLISHER_PORT=8280"
if "%FORMPUBLISHER_RELOAD%"=="0" (
  venv\Scripts\python.exe -m uvicorn app.main:app --host %FORMPUBLISHER_HOST% --port %FORMPUBLISHER_PORT%
) else (
  venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --host %FORMPUBLISHER_HOST% --port %FORMPUBLISHER_PORT%
)
