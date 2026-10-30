@echo off
rem StudentHub - Practical 10: starts XAMPP's PHP built-in web server for this folder and opens the login page.
rem MySQL must be running in the XAMPP Control Panel and user_registration.sql must be imported (see README.md).
cd /d "%~dp0"
set "PORT=8610"
set "PHP=C:\xampp\php\php.exe"
if not exist "%PHP%" set "PHP=php"
"%PHP%" -v >nul 2>nul
if errorlevel 1 (
    echo PHP was not found. Install XAMPP in C:\xampp, or add the folder containing php.exe to PATH.
    pause
    exit /b 1
)
echo Serving %CD%
echo Open http://127.0.0.1:%PORT%/login.php
echo Keep this window open while using the page. Press Ctrl+C to stop the server.
if /i not "%~1"=="nobrowser" start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:%PORT%/login.php"
"%PHP%" -S 127.0.0.1:%PORT% router.php
