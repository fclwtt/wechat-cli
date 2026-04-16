@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
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

REM Calculate yesterday (pure batch, no PowerShell)
echo [STEP] Calculating date... >> "%LOG_FILE%"

REM Get current date parts (format: YYYY/MM/DD or YYYY-MM-DD)
for /f "tokens=1-3 delims=/-. " %%a in ("%date%") do (
    set YEAR=%%a
    set MONTH=%%b
    set DAY=%%c
)

REM Remove leading zeros for math
set /a DAY_NUM=1%DAY%-100
set /a MONTH_NUM=1%MONTH%-100
set /a YEAR_NUM=%YEAR%

REM Subtract 1 day
set /a DAY_NUM=%DAY_NUM%-1

REM Handle month boundaries
if %DAY_NUM% leq 0 (
    set /a MONTH_NUM=%MONTH_NUM%-1
    if %MONTH_NUM% leq 0 (
        set /a MONTH_NUM=12
        set /a YEAR_NUM=%YEAR_NUM%-1
    )
    REM Days in previous month (approximate, works for most cases)
    if %MONTH_NUM%==1 set DAY_NUM=31
    if %MONTH_NUM%==2 set DAY_NUM=28
    if %MONTH_NUM%==3 set DAY_NUM=31
    if %MONTH_NUM%==4 set DAY_NUM=30
    if %MONTH_NUM%==5 set DAY_NUM=31
    if %MONTH_NUM%==6 set DAY_NUM=30
    if %MONTH_NUM%==7 set DAY_NUM=31
    if %MONTH_NUM%==8 set DAY_NUM=31
    if %MONTH_NUM%==9 set DAY_NUM=30
    if %MONTH_NUM%==10 set DAY_NUM=31
    if %MONTH_NUM%==11 set DAY_NUM=30
    if %MONTH_NUM%==12 set DAY_NUM=31
)

REM Format with leading zeros
if %DAY_NUM% lss 10 set DAY=0%DAY_NUM%
if %DAY_NUM% geq 10 set DAY=%DAY_NUM%
if %MONTH_NUM% lss 10 set MONTH=0%MONTH_NUM%
if %MONTH_NUM% geq 10 set MONTH=%MONTH_NUM%

set YESTERDAY=%YEAR_NUM%-%MONTH%-%DAY%
echo [OK] YESTERDAY=%YESTERDAY% >> "%LOG_FILE%"

REM Output directory
set OUTPUT_DIR=E:\wechat-chats-backup
set INDEX_DIR=%OUTPUT_DIR%\daily-index
set INDEX_FILE=%INDEX_DIR%\%YESTERDAY%.txt

if not exist "%INDEX_DIR%" mkdir "%INDEX_DIR%"

echo [STEP] Starting export... >> "%LOG_FILE%"

"%~dp0wechat-cli.exe" export-all-accounts --output "%OUTPUT_DIR%" --active-since "%YESTERDAY%" --index-file "%INDEX_FILE%" >> "%LOG_FILE%" 2>&1

echo [DONE] Completed at %time% >> "%LOG_FILE%"
exit /b 0