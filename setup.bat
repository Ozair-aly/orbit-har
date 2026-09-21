@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo           ORBIT-HAR -- OFFLINE WINDOWS SETUP
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found on PATH.
    echo Please install Python 3.10 or 3.11 from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% detected.

:: 2. Check Node.js
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not found on PATH.
    echo Please install Node.js (v18, v20, or v22) from https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do set NODE_VER=%%v
echo [OK] Node.js %NODE_VER% detected.

:: 3. Create Python Virtual Environment
echo.
echo [1/5] Setting up Python virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Created .venv
) else (
    echo [OK] Existing .venv found.
)

:: 4. Install Python Dependencies
echo.
echo [2/5] Installing Python dependencies into .venv...
if exist "wheels\*.whl" (
    echo Installing from local offline wheels cache...
    .venv\Scripts\pip.exe install --no-index --find-links=wheels -r requirements.txt matplotlib
) else (
    echo Installing from online requirements.txt...
    .venv\Scripts\pip.exe install -r requirements.txt matplotlib
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed.

:: 5. Setup YOLO11n Model Weights
echo.
echo [3/5] Verifying AI Model Weights (yolo11n.pt)...
if not exist "camera\yolo11n.pt" (
    if exist "models\yolo11n.pt" (
        copy /y "models\yolo11n.pt" "camera\yolo11n.pt" >nul
        echo [OK] Copied yolo11n.pt to camera directory.
    ) else if exist "yolo11n.pt" (
        if not exist "models" mkdir models
        copy /y "yolo11n.pt" "models\yolo11n.pt" >nul
        copy /y "yolo11n.pt" "camera\yolo11n.pt" >nul
        echo [OK] Copied yolo11n.pt to models and camera directories.
    ) else (
        echo Downloading yolo11n.pt weights via Python...
        .venv\Scripts\python.exe -c "import os, shutil; from ultralytics import YOLO; model = YOLO('yolo11n.pt'); os.makedirs('models', exist_ok=True); os.makedirs('camera', exist_ok=True); shutil.copy('yolo11n.pt', 'models/yolo11n.pt'); shutil.copy('yolo11n.pt', 'camera/yolo11n.pt')"
    )
)
if exist "camera\yolo11n.pt" (
    echo [OK] yolo11n.pt is ready locally.
) else (
    echo [WARNING] Could not locate or download yolo11n.pt.
)

:: 6. Install Frontend Dependencies
echo.
echo [4/5] Installing React dashboard dependencies...
cd /d "%~dp0\orbit-har-dashboard"
cmd /c npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
)
echo [OK] Frontend packages installed.

:: 7. Build Frontend Production Assets
echo.
echo [5/5] Building frontend production bundle...
cmd /c npm run build
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)
cd /d "%~dp0"
echo [OK] Production build created in orbit-har-dashboard\dist

echo.
echo ================================================================
echo           ORBIT-HAR SETUP COMPLETED SUCCESSFULLY!
echo ================================================================
echo You are now ready for 100%% OFFLINE operation.
echo To launch the complete application, run: start.bat
echo To stop all services, run: stop.bat
echo.
pause
