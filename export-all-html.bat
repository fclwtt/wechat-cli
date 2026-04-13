@echo off
chcp 65001 >nul
REM 微信聊天记录一键导出工具（多账号版本）

echo ============================================================
echo   WeChat Chat Export Tool (HTML) - Multi-Account
echo ============================================================
echo.

REM 检查当前目录是否有 wechat-cli.exe
if not exist "%~dp0wechat-cli.exe" (
    echo [ERROR] wechat-cli.exe not found
    echo Make sure this script and wechat-cli.exe are in the same folder
    pause
    exit /b 1
)

set CLI_PATH=%~dp0wechat-cli.exe
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup

echo Tool: %CLI_PATH%
echo Output: %OUTPUT_DIR%
echo.

REM 运行导出命令（多账号）
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --copy-media --limit 2000 --max-chats 100

echo.
echo Opening output folder...
explorer "%OUTPUT_DIR%"
pause