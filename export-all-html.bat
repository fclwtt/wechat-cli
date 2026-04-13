@echo off
chcp 65001 >nul
REM 微信聊天记录 HTML 导出工具
REM 双击运行即可导出所有聊天记录为美观的 HTML 页面

setlocal enabledelayedexpansion

echo ============================================================
echo   微信聊天记录导出工具 (HTML版)
echo ============================================================
echo.

REM 检查当前目录是否有 wechat-cli.exe
if not exist "%~dp0wechat-cli.exe" (
    echo [错误] 找不到 wechat-cli.exe
    echo.
    echo 请确保此脚本和 wechat-cli.exe 在同一目录
    pause
    exit /b 1
)

REM 设置路径
set CLI_PATH=%~dp0wechat-cli.exe
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup

echo 工具位置: %CLI_PATH%
echo 输出目录: %OUTPUT_DIR%
echo.

REM 创建输出目录
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM 获取会话列表
echo [1/2] 正在获取会话列表...
"%CLI_PATH%" sessions --format text > "%OUTPUT_DIR%\sessions_temp.txt" 2>nul

if not exist "%OUTPUT_DIR%\sessions_temp.txt" (
    echo [错误] 获取会话列表失败
    echo 请先运行: wechat-cli.exe init
    pause
    exit /b 1
)

REM 统计会话数量
set count=0
for /f "skip=1 tokens=*" %%a in ('type "%OUTPUT_DIR%\sessions_temp.txt"') do (
    set /a count+=1
)
echo 找到 %count% 个会话
echo.

REM 导出每个会话
echo [2/2] 正在导出聊天记录...
set exported=0

for /f "skip=1 tokens=1" %%a in ('type "%OUTPUT_DIR%\sessions_temp.txt"') do (
    set "chat_name=%%a"
    echo   导出: !chat_name!

    "%CLI_PATH%" export-html "!chat_name!" --output "%OUTPUT_DIR%" --copy-media 2>nul
    if !errorlevel! equ 0 (
        set /a exported+=1
    )
)

REM 清理临时文件
del "%OUTPUT_DIR%\sessions_temp.txt" 2>nul

echo.
echo ============================================================
echo   导出完成!
echo ============================================================
echo.
echo 已导出 %exported% 个聊天
echo 输出目录: %OUTPUT_DIR%
echo.
echo 使用方法:
echo   1. 打开文件夹: %OUTPUT_DIR%
echo   2. 进入任意聊天目录
echo   3. 双击 index.html 即可查看聊天记录
echo.
explorer "%OUTPUT_DIR%"
pause