@echo off
chcp 65001 >nul
title WeChat Chat Export - Daily Update (Hidden)

REM Check if wechat-cli.exe exists
if not exist "%~dp0wechat-cli.exe" (
    exit /b 1
)

set CLI_PATH=%~dp0wechat-cli.exe

REM Calculate yesterday's date
for /f "tokens=* %%a in ('powershell -command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"' 2>nul) do set YESTERDAY=%%a

REM Set output directory
set OUTPUT_DIR=E:\wechat-chats-backup

REM Set index file path
set INDEX_DIR=%OUTPUT_DIR%\daily-index
set INDEX_FILE=%INDEX_DIR%\%YESTERDAY%.txt

REM Create index directory
if not exist "%INDEX_DIR%" mkdir "%INDEX_DIR%"

REM Run daily update (only chats with messages yesterday, export FULL history, generate index)
"%CLI_PATH%" export-all-accounts --output "%OUTPUT_DIR%" --active-since "%YESTERDAY%" --index-file "%INDEX_FILE%"

exit /b 0