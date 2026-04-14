@echo off
chcp 65001 >nul
title 微信聊天记录全量导出

echo ============================================================
echo   微信聊天记录全量导出（多账号版）
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
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup

echo 工具: %CLI_PATH%
echo 输出: %OUTPUT_DIR%
echo.
echo 正在导出所有聊天记录...
echo.

REM 运行导出命令（多账号，纯文字版）
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --limit 2000 --max-chats 100

echo.
echo 导出完成！
echo.
echo 正在打开输出文件夹...
explorer "%OUTPUT_DIR%"
pause