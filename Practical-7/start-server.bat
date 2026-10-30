@echo off
rem StudentHub - Practical 7: starts XAMPP's PHP built-in web server for this folder and opens the form.
rem (Alternative: copy the Practical-7 folder into C:\xampp\htdocs and use Apache - see README.md.)
cd /d "%~dp0"
set "PORT=8607"
set "PHP=C:\xampp\php\php.exe"
if not exist "%PHP%" set "PHP=php"
"%PHP%" -v >nul 2>nul
if errorlevel 1 (
    echo PHP was not found. Install XAMPP in C:\xampp, or add the folder containing php.exe to PATH.
    pause
    exit /b 1
)
echo Serving %CD%
echo Open http://127.0.0.1:%PORT%/index.php
echo Keep this window open while using the form. Press Ctrl+C to stop the server.
if /i not "%~1"=="nobrowser" start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:%PORT%/index.php"
"%PHP%" -S 127.0.0.1:%PORT% router.php
