@echo off
chcp 65001 >nul
title WeChat Chat Export - Export All

echo ============================================================
echo   WeChat Chat Export Tool - Export All (Multi-Account)
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
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup

echo Tool: %CLI_PATH%
echo Output: %OUTPUT_DIR%
echo.
echo Exporting all chat records...
echo.

REM Run export command (multi-account, text-only)
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --limit 2000 --max-chats 100

echo.
echo Export Complete!
echo.
echo Opening output folder...
explorer "%OUTPUT_DIR%"
pause