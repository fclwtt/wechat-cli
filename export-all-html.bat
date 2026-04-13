@echo off
REM 微信聊天记录 HTML 导出工具
REM 双击运行即可导出所有聊天记录为美观的 HTML 页面

setlocal enabledelayedexpansion

echo ============================================================
echo   微信聊天记录导出工具 (HTML版)
echo ============================================================
echo.

REM 检查 wechat-cli
where wechat-cli.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 找不到 wechat-cli.exe
    echo.
    echo 请将此脚本放在 wechat-cli.exe 同目录下运行
    echo 或者将 wechat-cli.exe 所在目录添加到系统 PATH
    pause
    exit /b 1
)

REM 设置输出目录
set OUTPUT_DIR=%USERPROFILE%\wechat-chats-backup
echo 输出目录: %OUTPUT_DIR%
echo.

REM 创建输出目录
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM 获取会话列表
echo [1/2] 正在获取会话列表...
wechat-cli.exe sessions --format text > sessions_temp.txt

REM 统计会话数量
set count=0
for /f "skip=1 tokens=*" %%a in (sessions_temp.txt) do (
    set /a count+=1
)
echo 找到 %count% 个会话
echo.

REM 导出每个会话
echo [2/2] 正在导出聊天记录...
set exported=0

for /f "skip=1 tokens=1" %%a in (sessions_temp.txt) do (
    set "chat_name=%%a"
    echo   导出: !chat_name!

    REM 清理文件名中的特殊字符
    set "safe_name=!chat_name!"
    set "safe_name=!safe_name:/=_!"
    set "safe_name=!safe_name:\=_!"
    set "safe_name=!safe_name::=_!"
    set "safe_name=!safe_name:*=_!"
    set "safe_name=!safe_name:?=_!"
    set "safe_name=!safe_name:"=_!"
    set "safe_name=!safe_name:<=_!"
    set "safe_name=!safe_name:>=_!"
    set "safe_name=!safe_name:|=_!"

    wechat-cli.exe export-html "!chat_name!" --output "%OUTPUT_DIR%" --copy-media 2>nul
    set /a exported+=1
)

REM 清理临时文件
del sessions_temp.txt

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
pause