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

REM Get today's date using WMIC (reliable, locale-independent)
echo [STEP] Getting date via WMIC... >> "%LOG_FILE%"
for /f "skip=1 tokens=1-3 delims=." %%a in ('wmic os get localdatetime') do (
    set TODAY_RAW=%%a%%b%%c
)

REM WMIC returns: 20260416181436.55xxxxx (YYYYMMDDHHMMSS...)
REM Extract YYYY, MM, DD
set TODAY_RAW=%TODAY_RAW:~0,8%
set YEAR=%TODAY_RAW:~0,4%
set MONTH=%TODAY_RAW:~4,2%
set DAY=%TODAY_RAW:~6,2%

echo [OK] TODAY=%YEAR%-%MONTH%-%DAY% >> "%LOG_FILE%"

REM Calculate yesterday (subtract 1 day)
set /a DAY_NUM=1%DAY%-100
set /a MONTH_NUM=1%MONTH%-100
set /a YEAR_NUM=%YEAR%

set /a DAY_NUM=%DAY_NUM%-1

REM Handle month boundaries
if %DAY_NUM% leq 0 (
    set /a MONTH_NUM=%MONTH_NUM%-1
    if %MONTH_NUM% leq 0 (
        set /a MONTH_NUM=12
        set /a YEAR_NUM=%YEAR_NUM%-1
    )
    REM Days in each month
    for %%m in (1 3 5 7 8 10 12) do if %MONTH_NUM%==%%m set DAY_NUM=31
    for %%m in (4 6 9 11) do if %MONTH_NUM%==%%m set DAY_NUM=30
    if %MONTH_NUM%==2 set DAY_NUM=28
)

REM Format with leading zeros
if %DAY_NUM% lss 10 (set DAY=0%DAY_NUM%) else (set DAY=%DAY_NUM%)
if %MONTH_NUM% lss 10 (set MONTH=0%MONTH_NUM%) else (set MONTH=%MONTH_NUM%)

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