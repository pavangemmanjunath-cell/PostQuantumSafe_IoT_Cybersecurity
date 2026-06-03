@echo off
REM ========================================================
REM TIPPSS SafeGuard-PQ Dashboard Launcher (Windows)
REM ========================================================

echo.
echo === TIPPSS SafeGuard-PQ Dashboard ===
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo and check "Add Python to PATH" during install.
    pause
    exit /b 1
)

REM Check if virtual environment exists; create if not
if not exist "venv\" (
    echo [1/3] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install/update requirements
echo [2/3] Installing dashboard dependencies...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

REM Launch Streamlit
echo [3/3] Starting dashboard...
echo.
echo The dashboard will open in your browser at:
echo   http://localhost:8501
echo.
echo Press Ctrl+C to stop the dashboard.
echo ----------------------------------------
streamlit run dashboard.py

pause
