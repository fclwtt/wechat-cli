@echo off
chcp 65001 >nul
REM 微信聊天记录每日增量导出工具（多账号版本）

setlocal enabledelayedexpansion

echo ============================================================
echo   微信聊天记录每日导出 (HTML版) - Multi-Account
echo ============================================================
echo.

REM 检查当前目录是否有 wechat-cli.exe
if not exist "%~dp0wechat-cli.exe" (
    echo [错误] 找不到 wechat-cli.exe
    pause
    exit /b 1
)

set CLI_PATH=%~dp0wechat-cli.exe

REM 计算昨天的日期
for /f "tokens=*" %%a in ('powershell -command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set YESTERDAY=%%a

echo 导出日期: %YESTERDAY%
echo.

REM 设置输出目录
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup\daily\%YESTERDAY%
echo 输出目录: %OUTPUT_DIR%
echo.

REM 运行多账号每日导出
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --copy-media --limit 500 --max-chats 50 --start-time "%YESTERDAY%" --end-time "%YESTERDAY%"

echo.
echo 导出完成: %OUTPUT_DIR%
explorer "%OUTPUT_DIR%"
pause