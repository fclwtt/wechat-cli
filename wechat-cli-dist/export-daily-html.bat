@echo off
chcp 65001 >nul
title WeChat Chat Export - Daily Update

echo ============================================================
echo   WeChat Chat Export Tool - Daily Update
echo ============================================================
echo.

REM Check if wechat-cli.exe exists
if not exist "%~dp0wechat-cli.exe" (
    echo [ERROR] wechat-cli.exe not found
    echo Please ensure this script and wechat-cli.exe are in the same folder
    pause
    exit /b 1
)

set CLI_PATH=%~dp0wechat-cli.exe

REM Calculate yesterday's date
for /f "tokens=*" %%a in ('powershell -command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set YESTERDAY=%%a

echo Active Since: %YESTERDAY% (yesterday)
echo.

REM Set output directory (same as full export)
set OUTPUT_DIR=E:\wechat-chats-backup
echo Output: %OUTPUT_DIR%
echo.

echo Updating chat records...
echo Note: Only chats with new messages yesterday will be updated (FULL HISTORY)
echo.

REM Run daily update (only chats with messages yesterday, export FULL history)
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --active-since "%YESTERDAY%"

echo.
echo ============================================================
echo   Update Complete!
echo ============================================================
echo.
echo Output: %OUTPUT_DIR%
echo.
echo Note:
echo   - Only chats with new messages yesterday were updated
echo   - Full history exported (no message limit)
echo   - HTML files were overwritten with latest content
echo   - Chats without new messages were skipped
echo.
echo Opening output folder...
explorer "%OUTPUT_DIR%"
pause