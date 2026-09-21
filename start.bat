@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo           ORBIT-HAR -- STARTING OFFLINE SYSTEM
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. Validate Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment (.venv) not found!
    echo Please run setup.bat first while connected to the internet.
    pause
    exit /b 1
)

:: 2. Validate Model Weights
if not exist "camera\yolo11n.pt" (
    if exist "models\yolo11n.pt" (
        copy /y "models\yolo11n.pt" "camera\yolo11n.pt" >nul
    ) else if exist "yolo11n.pt" (
        copy /y "yolo11n.pt" "camera\yolo11n.pt" >nul
    )
)

if not exist "camera\yolo11n.pt" (
    echo [WARNING] camera\yolo11n.pt not found. Container Orientation experiment might fail if offline.
)

:: 3. Terminate Any Stale Processes on Target Ports
echo [1/4] Checking ports 8000, 8010, 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8010" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: 4. Start FastAPI Backend
echo [2/4] Starting ORBIT-HAR Backend on http://127.0.0.1:8000 ...
start "ORBIT-HAR Backend" cmd /k "cd /d "%~dp0backend" && set PYTHONIOENCODING=utf-8 && set PYTHONUTF8=1 && "..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000"

:: 5. Start Dashboard
echo [3/4] Starting ORBIT-HAR Dashboard on http://127.0.0.1:5173 ...
start "ORBIT-HAR Dashboard" cmd /k "cd /d "%~dp0orbit-har-dashboard" && npm run preview -- --port 5173 --host 127.0.0.1"

:: 6. Launch Browser
echo [4/4] Opening Dashboard in browser...
ping 127.0.0.1 -n 4 >nul
start http://localhost:5173

echo.
echo ================================================================
echo           ORBIT-HAR IS RUNNING (OFFLINE MODE)
echo ================================================================
echo.
echo   * Dashboard:        http://localhost:5173
echo   * Backend API:      http://127.0.0.1:8000
echo   * WebSocket:        ws://127.0.0.1:8000/ws
echo   * Human 3D Mesh:    http://127.0.0.1:8010 (started on demand)
echo.
echo ================================================================
echo INSTRUCTIONS FOR SIH DEMONSTRATION:
echo   1. Keep the "ORBIT-HAR Backend" and "ORBIT-HAR Dashboard" windows open.
echo   2. On the dashboard, navigate to "Experiments" to pick and start an experiment.
echo   3. For Human Mesh tracking, navigate to "3D Human Mesh" and click START.
echo   4. To completely STOP all services, double-click: stop.bat
echo ================================================================
echo.
pause
