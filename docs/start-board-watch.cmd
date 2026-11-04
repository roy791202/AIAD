@echo off
setlocal
set PORT=28789
cd /d "%~dp0"

python -u board_watch.py --replace-stale --port %PORT% --no-browser
if errorlevel 2 (
  echo port %PORT% refused
  pause
  exit /b 2
)

powershell -NoProfile -Command "try{(New-Object Net.Sockets.TcpClient('127.0.0.1',%PORT%)).Close();exit 0}catch{exit 1}" >nul 2>&1
if %ERRORLEVEL%==0 goto open

echo Starting SGenAxis board-watch http://127.0.0.1:%PORT%/
echo Add/edit tasks write back to PROJECT-BOARD.html
echo Agent dispatch is ON this port. Do not use 8788 HoneyBadgerCreator mailbox.
start "SGenAxis board-watch" /min cmd /c "python -u board_watch.py --port %PORT% --no-browser"

powershell -NoProfile -Command "for($n=0;$n -lt 40;$n++){try{(New-Object Net.Sockets.TcpClient('127.0.0.1',%PORT%)).Close();exit 0}catch{Start-Sleep -Milliseconds 250}};exit 1" >nul 2>&1
if not %ERRORLEVEL%==0 (
  echo board-watch did not bind 127.0.0.1:%PORT%
  echo Do not use port 8788 that is HoneyBadgerCreator mailbox.
  pause
  exit /b 1
)

:open
start "" "http://127.0.0.1:%PORT%/"
endlocal
