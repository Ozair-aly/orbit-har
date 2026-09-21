@echo off
echo ================================================================
echo           ORBIT-HAR -- STOPPING ALL LOCAL SERVICES
echo ================================================================
echo.

cd /d "%~dp0"

echo Stopping services on ports 8000, 8010, 5173...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8010" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [OK] All ORBIT-HAR processes have been stopped cleanly.
echo.
ping 127.0.0.1 -n 2 >nul
