@echo off
setlocal EnableDelayedExpansion

TITLE TorrentGuard Launcher
COLOR 0A

echo ============================================================
echo    TORRENTGUARD // SYSTEM STARTUP
echo ============================================================

:: 1. Check Python
echo [INIT] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERR] Python is not installed or not in PATH.
    echo        Please install Python 3.x and try again.
    pause
    exit /b 1
)
echo [OK] Python found.

:: 2. Install Dependencies
echo [INIT] Installing dependencies...
pip install -r requirements_loose.txt
if %errorlevel% neq 0 (
    echo [WARN] Dependency installation had issues. Attempting to proceed...
) else (
    echo [OK] Dependencies installed.
)

:: 3. Start qBittorrent
echo [INIT] Searching for qBittorrent...
set "QB_PATH="

:: Check common locations
if exist "C:\Program Files\qBittorrent\qbittorrent.exe" (
    set "QB_PATH=C:\Program Files\qBittorrent\qbittorrent.exe"
) else if exist "C:\Program Files (x86)\qBittorrent\qbittorrent.exe" (
    set "QB_PATH=C:\Program Files (x86)\qBittorrent\qbittorrent.exe"
)

if defined QB_PATH (
    echo [OK] Found qBittorrent at: "!QB_PATH!"
    echo [EXEC] Launching qBittorrent...
    start "" "!QB_PATH!"
    
    :: Wait a bit for it to start
    echo [WAIT] Waiting for qBittorrent to initialize...
    timeout /t 5 /nobreak >nul
) else (
    echo [WARN] qBittorrent not found in standard locations.
    echo        The application will run in MOCK MODE unless qBittorrent is running manually.
)

:: 4. Start API Server
echo [EXEC] Starting API Server...
:: Start in a new window so this script doesn't block
start "TorrentGuard Server" cmd /k "python api_server.py"

:: Wait for server to spin up
echo [WAIT] Waiting for server to become ready...
timeout /t 5 /nobreak >nul

:: 5. Launch Frontend
echo [EXEC] Launching Frontend...
start http://localhost:5000

echo ============================================================
echo    SYSTEM ONLINE
echo ============================================================
echo.
echo Press any key to exit this launcher (Server will keep running)...
pause >nul
