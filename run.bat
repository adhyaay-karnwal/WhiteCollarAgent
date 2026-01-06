@echo off
setlocal EnableDelayedExpansion

REM =================CONFIGURATION=================
REM Define paths relative to where this script is run
set VM_DIR=.\core\gui
set PYTHON_CMD=python -m core.main

REM IMPORTANT: Ensure this matches your docker-compose ports
set READY_PORT=3000
set READY_HOST=localhost
set MAX_WAIT_SECONDS=60
REM ===============================================


echo --- Starting Launch Sequence ---

REM 1. Start the Docker VM
echo [1/3] Launching VM Docker containers in background...

REM pushd changes directory temporarily
pushd %VM_DIR%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not find directory: %VM_DIR%
    goto :error_exit
)

docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Docker compose.
    popd
    goto :error_exit
)
REM popd returns to original directory
popd


REM 2. The Wait Loop
echo [2/3] Waiting for VM service to be ready on port %READY_PORT%...
set waited=0

:wait_loop
REM Use PowerShell to check TCP connection. It exits with 0 on success, 1 on fail.
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $client = New-Object System.Net.Sockets.TcpClient('%READY_HOST%', %READY_PORT%); $client.Close(); exit 0 } catch { exit 1 }" >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    goto :vm_ready
)

set /a waited+=1
if !waited! GEQ %MAX_WAIT_SECONDS% (
    goto :error_timeout
)

REM Print a dot without newline using set /p hack
<nul set /p=.
REM Wait 1 second
timeout /t 1 /nobreak >nul
goto :wait_loop

:vm_ready
echo.
echo [OK] VM Service is reachable!


REM 3. Start the Python Agent
echo [3/3] Launching Python Agent...
echo --------------------------------
echo WINDOWS NOTE: If using Ctrl+C, you may be prompted "Terminate batch job (Y/N)?".
echo Answer 'N' to let the Python app shut down cleanly.
echo Alternatively, use '/exit' or your app's defined quit hotkey.
echo --------------------------------

REM Run Python in the foreground. The script blocks here.
%PYTHON_CMD%

echo.
echo [i] Agent exited normally.
REM Fall through to cleanup

REM =================CLEANUP SECTION=================
:cleanup
echo.
echo --- Cleanup Initiated ---
echo [*] Stopping Docker VM containers...

pushd %VM_DIR% 2>nul
if %ERRORLEVEL% EQU 0 (
    docker compose down
    popd
)

echo Shutdown complete.
REM Exit script normally
goto :eof
REM =================================================


REM =================ERROR HANDLERS=================
:error_timeout
echo.
echo [ERROR] Timed out waiting for VM port %READY_PORT%.
goto :cleanup

:error_exit
echo [ERROR] Script aborted unexpectedly.
goto :cleanup