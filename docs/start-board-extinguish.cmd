@echo off
REM Deprecated name — does NOT admin-green.
REM 滅燈 = 實際做完後才改綠。此腳本改為列出下一張待做。
setlocal
cd /d "%~dp0\.."
echo poll_extinguish is locked. Listing next real work card instead:
python -u tools\board\poll_next_work.py --all
echo.
echo Finish work and open a PR. Only the high-level model or user may set Done/Blue, after independent TDD_PASS and PR merge.
endlocal
