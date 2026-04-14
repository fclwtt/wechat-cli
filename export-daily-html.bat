@echo off
chcp 65001 >nul
title 微信聊天记录每日导出

echo ============================================================
echo   微信聊天记录每日导出（多账号版）
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

REM 计算昨天的日期
for /f "tokens=*" %%a in ('powershell -command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set YESTERDAY=%%a

echo 导出日期: %YESTERDAY%（昨天）
echo.

REM 设置输出目录（独立目录，便于按日期查看）
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup\daily\%YESTERDAY%
echo 输出目录: %OUTPUT_DIR%
echo.

echo 正在导出昨天的聊天记录...
echo.

REM 运行每日导出（纯文字版，只导出昨天）
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --limit 500 --max-chats 50 --start-time "%YESTERDAY%" --end-time "%YESTERDAY%"

echo.
echo ============================================================
echo   导出完成！
echo ============================================================
echo.
echo 输出目录: %OUTPUT_DIR%
echo.
echo 说明：
echo   - 每日导出存储在独立目录（按日期）
echo   - 不覆盖也不合并到全量导出
echo   - 便于按日期查看增量消息
echo.
echo 正在打开输出文件夹...
explorer "%OUTPUT_DIR%"
pause