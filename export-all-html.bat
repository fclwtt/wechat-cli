@echo off
chcp 65001 >nul
REM 微信聊天记录 HTML 导出工具

setlocal enabledelayedexpansion

echo ============================================================
echo   WeChat Chat Export Tool (HTML)
echo ============================================================
echo.

REM 检查配置文件是否存在
set CONFIG_FILE=%USERPROFILE%\.wechat-cli\config.json
if not exist "%CONFIG_FILE%" (
    echo [ERROR] Config file not found!
    echo.
    echo Please run first: wechat-cli.exe init
    echo.
    pause
    exit /b 1
)

REM 检查当前目录是否有 wechat-cli.exe
if not exist "%~dp0wechat-cli.exe" (
    echo [ERROR] wechat-cli.exe not found
    echo Make sure this script and wechat-cli.exe are in the same folder
    pause
    exit /b 1
)

set CLI_PATH=%~dp0wechat-cli.exe
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup

echo Tool: %CLI_PATH%
echo Output: %OUTPUT_DIR%
echo.

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [1/2] Getting chat list...
"%CLI_PATH%" sessions --format text > "%OUTPUT_DIR%\sessions_temp.txt" 2>nul

if not exist "%OUTPUT_DIR%\sessions_temp.txt" (
    echo [ERROR] Failed to get sessions
    pause
    exit /b 1
)

set count=0
for /f "skip=1 tokens=*" %%a in ('type "%OUTPUT_DIR%\sessions_temp.txt"') do (
    set /a count+=1
)
echo Found %count% chats
echo.

if %count% equ 0 (
    echo [WARNING] No chats found
    echo Please check:
    echo   1. WeChat is running and logged in
    echo   2. wechat-cli.exe init was run successfully
    del "%OUTPUT_DIR%\sessions_temp.txt" 2>nul
    pause
    exit /b 0
)

echo [2/2] Exporting chats...
set exported=0

for /f "skip=1 tokens=1" %%a in ('type "%OUTPUT_DIR%\sessions_temp.txt"') do (
    set "chat_name=%%a"
    echo   Exporting: !chat_name!
    "%CLI_PATH%" export-html "!chat_name!" --output "%OUTPUT_DIR%" --copy-media 2>nul
    if !errorlevel! equ 0 (
        set /a exported+=1
    )
)

del "%OUTPUT_DIR%\sessions_temp.txt" 2>nul

echo.
echo ============================================================
echo   Export Complete
echo ============================================================
echo.
echo Exported: %exported% chats
echo Output: %OUTPUT_DIR%
echo.
echo Usage:
echo   1. Open folder: %OUTPUT_DIR%
echo   2. Enter any chat folder
echo   3. Double-click index.html to view
echo.

explorer "%OUTPUT_DIR%"
pause