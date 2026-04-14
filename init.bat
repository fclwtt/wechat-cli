@echo off
chcp 65001 >nul
title WeChat Chat Export - Init

echo.
echo ============================================
echo   WeChat Chat Export Tool - Initialize
echo ============================================
echo.
echo This script will:
echo   1. Detect WeChat process
echo   2. Extract decryption keys
echo   3. Save account configuration
echo.
echo Please ensure:
echo   - WeChat is logged in (all accounts if multiple)
echo   - WeChat window is open
echo.
echo ============================================
echo.

pause

echo.
echo [Start Initialization]
echo.

wechat-cli.exe init --all

echo.
echo ============================================
echo   Initialization Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Double-click export-all-html.bat to export all chats
echo   2. Double-click export-daily-html.bat for daily updates
echo.

pause