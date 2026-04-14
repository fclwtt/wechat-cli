@echo off
chcp 65001 >nul
title 微信聊天记录每日更新

echo ============================================================
echo   微信聊天记录每日更新（多账号版）
echo ============================================================
echo.

REM 检查当前目录是否有 wechat-cli.exe
if not exist "%~dp0wechat-cli.exe" (
    echo [错误] 找不到 wechat-cli.exe
    echo 请确保此脚本和 wechat-cli.exe 在同一文件夹
    pause
    exit /b 1
)

set CLI_PATH=%~dp0wechat-cli.exe

REM 计算最近7天的起始日期
for /f "tokens=*" %%a in ('powershell -command "(Get-Date).AddDays(-7).ToString('yyyy-MM-dd')"') do set START_DATE=%%a

echo 导出范围: %START_DATE% 至今（最近7天）
echo.

REM 设置输出目录（与全量导出同一目录）
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup
echo 输出目录: %OUTPUT_DIR%
echo.

echo 正在更新聊天记录...
echo 说明：本次导出会覆盖已有的 HTML 文件，更新为最新内容
echo.

REM 运行每日更新（导出到全量目录，最近7天）
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --limit 2000 --max-chats 100 --start-time "%START_DATE%"

echo.
echo ============================================================
echo   更新完成！
echo ============================================================
echo.
echo 输出目录: %OUTPUT_DIR%
echo.
echo 说明：
echo   - 已更新最近7天有新消息的聊天记录
echo   - HTML 文件已覆盖更新（保留最新内容）
echo   - 无新消息的聊天不会更新
echo.
echo 正在打开输出文件夹...
explorer "%OUTPUT_DIR%"
pause