@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title WeChat Daily Export (Hidden)

REM Log file (UTF-8)
set LOG_FILE=%~dp0export-daily-log.txt

REM Create empty UTF-8 log file
powershell -Command "[System.IO.File]::WriteAllText('%LOG_FILE%', '')" >nul 2>&1

REM Start
powershell -Command "Add-Content -Path '%LOG_FILE%' -Value '[START] %date% %time%' -Encoding UTF8" >nul 2>&1

REM Check exe
if not exist "%~dp0wechat-cli.exe" (
    powershell -Command "Add-Content -Path '%LOG_FILE%' -Value '[ERROR] wechat-cli.exe not found' -Encoding UTF8" >nul 2>&1
    exit /b 1
)
powershell -Command "Add-Content -Path '%LOG_FILE%' -Value '[OK] wechat-cli.exe found' -Encoding UTF8" >nul 2>&1

REM Output directory
set OUTPUT_DIR=E:\共享文件夹\wechat-chats-backup

powershell -Command "Add-Content -Path '%LOG_FILE%' -Value '[STEP] Starting daily export...' -Encoding UTF8" >nul 2>&1

REM Run daily export (--daily auto-calculates yesterday, skip existing) - UTF-8 output
"%~dp0wechat-cli.exe" export-all-accounts --output "%OUTPUT_DIR%" --daily --skip-existing 2>&1 | powershell -Command "$input | Add-Content -Path '%LOG_FILE%' -Encoding UTF8"

powershell -Command "Add-Content -Path '%LOG_FILE%' -Value '[DONE] Completed at %time%' -Encoding UTF8" >nul 2>&1
exit /b 0
