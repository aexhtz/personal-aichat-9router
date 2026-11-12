@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Python environment not found. Follow setup steps in README.md first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --console --name "Personal AI" --distpath "%~dp0dist" --workpath "%~dp0build\pyinstaller" --specpath "%~dp0build" --paths "%~dp0" personal_ai\chat.py
if errorlevel 1 goto failed
echo.
echo Built: dist\Personal AI.exe
echo Copy .env beside the EXE, then create a taskbar shortcut to the EXE.
pause
exit /b 0
:failed
echo Build failed. Check error output above.
pause
exit /b 1
