@echo off
REM 微信聊天记录每日增量导出工具
REM 导出昨天的聊天记录

setlocal enabledelayedexpansion

echo ============================================================
echo   微信聊天记录每日导出 (HTML版)
echo ============================================================
echo.

REM 检查 wechat-cli
where wechat-cli.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 找不到 wechat-cli.exe
    pause
    exit /b 1
)

REM 计算昨天的日期（Windows 批处理日期计算较复杂，这里用 PowerShell 辅助）
for /f "tokens=*" %%a in ('powershell -command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set YESTERDAY=%%a

echo 导出日期: %YESTERDAY%
echo.

REM 设置输出目录
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup\daily\%YESTERDAY%
echo 输出目录: %OUTPUT_DIR%
echo.

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM 获取会话并导出
wechat-cli.exe sessions --format text > sessions_temp.txt

for /f "skip=1 tokens=1" %%a in (sessions_temp.txt) do (
    set "chat_name=%%a"
    echo   导出: !chat_name!
    wechat-cli.exe export-html "!chat_name!" --output "%OUTPUT_DIR%" --start-time "%YESTERDAY%" --end-time "%YESTERDAY%" 2>nul
)

del sessions_temp.txt

echo.
echo 导出完成: %OUTPUT_DIR%
pause