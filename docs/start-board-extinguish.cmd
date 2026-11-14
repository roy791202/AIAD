@echo off
REM Deprecated name — does NOT admin-green.
REM 滅燈 = 實際做完後才改綠。此腳本改為列出下一張待做。
setlocal
cd /d "%~dp0\.."
echo poll_extinguish is locked. Listing next real work card instead:
python -u tools\board\poll_next_work.py --all
echo.
echo Finish work, verify (cargo test / tauri dev), then green the card.
endlocal
