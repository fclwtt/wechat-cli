@echo off
chcp 65001 >nul
title WeChat Chat Export - Daily Update (Hidden)

REM 日志文件
set LOG_FILE=%~dp0export-daily-log.txt

REM 写入开始时间
echo [%date% %time%] 开始执行 >> "%LOG_FILE%"

REM Check if wechat-cli.exe exists
if not exist "%~dp0wechat-cli.exe" (
    echo [%date% %time%] 错误: wechat-cli.exe 不存在 >> "%LOG_FILE%"
    exit /b 1
)

echo [%date% %time%] wechat-cli.exe 存在 >> "%LOG_FILE%"

set CLI_PATH=%~dp0wechat-cli.exe

REM Calculate yesterday's date
for /f "tokens=* %%a in ('powershell -command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"' 2>nul) do set YESTERDAY=%%a

echo [%date% %time%] 日期: %YESTERDAY% >> "%LOG_FILE%"

REM Set output directory
set OUTPUT_DIR=E:\wechat-chats-backup

REM Set index file path
set INDEX_DIR=%OUTPUT_DIR%\daily-index
set INDEX_FILE=%INDEX_DIR%\%YESTERDAY%.txt

REM Create index directory
if not exist "%INDEX_DIR%" mkdir "%INDEX_DIR%"

echo [%date% %time%] 开始导出... >> "%LOG_FILE%"

REM Run daily update (only chats with messages yesterday, export FULL history, generate index)
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --active-since "%YESTERDAY%" --index-file "%INDEX_FILE%" >> "%LOG_FILE%" 2>&1

echo [%date% %time%] 导出完成 >> "%LOG_FILE%"

exit /b 0