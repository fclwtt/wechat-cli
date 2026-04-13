@echo off
chcp 65001 >nul
REM 微信聊天记录每日增量导出工具
REM 导出昨天的聊天记录

setlocal enabledelayedexpansion

echo ============================================================
echo   微信聊天记录每日导出 (HTML版)
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

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM 获取会话并导出
"%CLI_PATH%" sessions --format text > "%OUTPUT_DIR%\sessions_temp.txt" 2>nul

for /f "skip=1 tokens=1" %%a in ('type "%OUTPUT_DIR%\sessions_temp.txt"') do (
    set "chat_name=%%a"
    echo   导出: !chat_name!
    "%CLI_PATH%" export-html "!chat_name!" --output "%OUTPUT_DIR%" --start-time "%YESTERDAY%" --end-time "%YESTERDAY%" 2>nul
)

del "%OUTPUT_DIR%\sessions_temp.txt" 2>nul

echo.
echo 导出完成: %OUTPUT_DIR%
explorer "%OUTPUT_DIR%"
pause