@echo off
setlocal

python --version > nul 2>&1
if %errorlevel% equ 0 (
    echo Python is already installed.
) else (
    echo Downloading Python 3.11...
    curl -o python311.exe https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
    echo Installing Python 3.11...
    python311.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    python --version > nul 2>&1
    if %errorlevel% neq 0 (
        echo Failed to install Python. Exiting.
        exit /b 1
    )
)

python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install Python packages. Cleaning up...
    rd /s /q ServeLite
    exit /b 1
)

endlocal
