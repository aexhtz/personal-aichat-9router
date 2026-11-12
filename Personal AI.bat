@echo off
setlocal
set "APP_DIR=%~dp0"

if not exist "%APP_DIR%personal_ai\chat.py" (
    echo Project not found. Keep this launcher in project folder or update APP_DIR in this file.
    pause
    exit /b 1
)
if not exist "%APP_DIR%\.venv\Scripts\python.exe" (
    echo Python environment not found. Follow setup steps in README.md first.
    pause
    exit /b 1
)

pushd "%APP_DIR%"
".venv\Scripts\python.exe" -m personal_ai.chat
if errorlevel 1 pause
popd
