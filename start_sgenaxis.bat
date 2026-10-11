@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw -m sgenaxis
    exit /b 0
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "SGenAxis" python -m sgenaxis
    exit /b 0
)

echo 找不到 Python，請先安裝 Python 3.10 以上並加入 PATH。
pause
exit /b 1
