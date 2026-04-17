@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title WeChat Daily Export (Hidden)

REM Log file
set LOG_FILE=%~dp0export-daily-log.txt

REM Start
echo [START] %date% %time% > "%LOG_FILE%"

REM Check exe
if not exist "%~dp0wechat-cli.exe" (
    echo [ERROR] wechat-cli.exe not found >> "%LOG_FILE%"
    exit /b 1
)
echo [OK] wechat-cli.exe found >> "%LOG_FILE%"

REM Output directory
set OUTPUT_DIR=E:\共享文件夹\wechat-chats-backup

echo [STEP] Starting daily export... >> "%LOG_FILE%"

REM Run daily export (--daily auto-calculates yesterday, generates index)
"%~dp0wechat-cli.exe" export-all-accounts --output "%OUTPUT_DIR%" --daily >> "%LOG_FILE%" 2>&1

echo [DONE] Completed at %time% >> "%LOG_FILE%"
exit /b 0