@echo off
chcp 65001 >nul
title WeChat Chat Export - Daily Update (Hidden)

REM Log file
set LOG_FILE=%~dp0export-daily-log.txt

REM Clear log and write start time
echo [START] %date% %time% > "%LOG_FILE%"

REM Check if wechat-cli.exe exists
if not exist "%~dp0wechat-cli.exe" (
    echo [ERROR] wechat-cli.exe not found >> "%LOG_FILE%"
    exit /b 1
)

echo [OK] wechat-cli.exe found >> "%LOG_FILE%"

set CLI_PATH=%~dp0wechat-cli.exe

REM Calculate yesterday's date (usebackq to allow nested quotes)
echo [STEP] Calculating yesterday date... >> "%LOG_FILE%"
for /f "usebackq tokens=* %%a in (`powershell -command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"`) do set YESTERDAY=%%a

echo [OK] YESTERDAY=%YESTERDAY% >> "%LOG_FILE%"

REM Set output directory
set OUTPUT_DIR=E:\wechat-chats-backup

REM Set index file path
set INDEX_DIR=%OUTPUT_DIR%\daily-index
set INDEX_FILE=%INDEX_DIR%\%YESTERDAY%.txt

REM Create index directory
if not exist "%INDEX_DIR%" mkdir "%INDEX_DIR%"

echo [STEP] Starting export... >> "%LOG_FILE%"
echo [CMD] %CLI_PATH% export-all-accounts --output %OUTPUT_DIR% --active-since %YESTERDAY% --index-file %INDEX_FILE% >> "%LOG_FILE%"

REM Run daily update (only chats with messages yesterday, export FULL history, generate index)
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --active-since "%YESTERDAY%" --index-file "%INDEX_FILE%" >> "%LOG_FILE%" 2>&1

echo [DONE] Export completed at %time% >> "%LOG_FILE%"

exit /b 0