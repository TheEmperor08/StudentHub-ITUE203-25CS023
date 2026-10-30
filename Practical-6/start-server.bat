@echo off
rem StudentHub - Practical 6: starts a local web server in this folder and opens the page.
rem fetch() and JavaScript modules do not work when the page is opened by double-clicking (file://).
cd /d "%~dp0"
set PORT=8606
rem Use the first Python that actually runs (a "py" launcher can point to a removed Python version).
set PY=
python -c "import http.server" >nul 2>nul && set PY=python
if not defined PY (
    py -3 -c "import http.server" >nul 2>nul && set PY=py -3
)
if not defined PY (
    echo Python was not found. Install Python 3 from python.org and tick "Add python.exe to PATH".
    pause
    exit /b 1
)
echo Serving %CD%
echo Open http://127.0.0.1:%PORT%/directory.html
echo Keep this window open while using the page. Press Ctrl+C to stop the server.
if /i not "%~1"=="nobrowser" start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:%PORT%/directory.html"
%PY% -m http.server %PORT% --bind 127.0.0.1
