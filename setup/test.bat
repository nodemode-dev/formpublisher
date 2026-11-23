@echo off
setlocal
set "ROOT=%~dp0.."
set "WHICH=%~1"
if "%WHICH%"=="" set "WHICH=all"
set "REST=%2 %3 %4 %5 %6 %7 %8 %9"
set "FAIL=0"
set "KNOWN=0"
for %%L in (all unit engine) do if /i "%WHICH%"=="%%L" set "KNOWN=1"
if "%KNOWN%"=="0" ( echo [formpublisher] unknown test layer: %WHICH% ^(use unit, engine or nothing for all^) & exit /b 2 )
set "DO=0"
if /i "%WHICH%"=="all" set "DO=1"
if /i "%WHICH%"=="unit" set "DO=1"
if "%DO%"=="1" (
  if not exist "%ROOT%\frontend\node_modules\vitest" ( echo [formpublisher] error: the interface packages are missing, run formpublisher.bat install & exit /b 1 )
  echo [formpublisher] interface logic ^(vitest^)
  pushd "%ROOT%\frontend"
  call npx vitest run %REST% || set "FAIL=1"
  popd
)
set "DO=0"
if /i "%WHICH%"=="all" set "DO=1"
if /i "%WHICH%"=="engine" set "DO=1"
set "PY=%ROOT%\backend\venv\Scripts\python.exe"
if "%DO%"=="1" (
  if not exist "%PY%" ( echo [formpublisher] error: the backend venv is missing, run formpublisher.bat install & exit /b 1 )
  "%PY%" -c "import pytest" >nul 2>&1 || ( echo [formpublisher] error: pytest is missing from the backend venv, run backend\venv\Scripts\python.exe -m pip install -r backend\requirements-test.txt & exit /b 1 )
  echo [formpublisher] engine ^(pytest^)
  pushd "%ROOT%"
  "%PY%" -m pytest -q backend\tests %REST% || set "FAIL=1"
  popd
)
exit /b %FAIL%
