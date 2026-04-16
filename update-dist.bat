@echo off
chcp 65001 >nul
title Update wechat-cli-dist

echo ============================================================
echo   wechat-cli-dist 一键更新
echo ============================================================
echo.

REM 设置源码目录（同级目录）
set SOURCE_DIR=%~dp0..\wechat-cli
set DIST_DIR=%~dp0

echo 源码目录: %SOURCE_DIR%
echo 输出目录: %DIST_DIR%
echo.

REM 检查源码目录是否存在
if not exist "%SOURCE_DIR%" (
    echo [错误] 源码目录不存在: %SOURCE_DIR%
    echo 请先 git clone 到该目录
    pause
    exit /b 1
)

REM 1. 拉取最新源码
echo [1/3] 拉取最新源码...
cd /d "%SOURCE_DIR%"
git pull
if errorlevel 1 (
    echo [警告] git pull 失败，继续构建...
)
echo.

REM 2. 构建 exe
echo [2/3] 构建 exe...
python build_windows.py
if errorlevel 1 (
    echo [错误] 构建失败
    pause
    exit /b 1
)
echo.

REM 3. 复制文件到 dist 目录
echo [3/3] 复制文件到 dist 目录...

REM 复制 exe
copy /y "%SOURCE_DIR%\dist\wechat-cli.exe" "%DIST_DIR%\wechat-cli.exe" >nul
echo   wechat-cli.exe

REM 复制 bat 文件
copy /y "%SOURCE_DIR%\export-daily-html.bat" "%DIST_DIR%\export-daily-html.bat" >nul
copy /y "%SOURCE_DIR%\export-daily-html-hidden.bat" "%DIST_DIR%\export-daily-html-hidden.bat" >nul
copy /y "%SOURCE_DIR%\export-all-accounts.bat" "%DIST_DIR%\export-all-accounts.bat" >nul
copy /y "%SOURCE_DIR%\init.bat" "%DIST_DIR%\init.bat" >nul
echo   bat 文件

REM 复制 vbs 文件
copy /y "%SOURCE_DIR%\export-daily-html-silent.vbs" "%DIST_DIR%\export-daily-html-silent.vbs" >nul
echo   vbs 文件

REM 复制 ps1 文件
copy /y "%SOURCE_DIR%\setup-scheduled-task.ps1" "%DIST_DIR%\setup-scheduled-task.ps1" >nul
echo   ps1 文件

echo.
echo ============================================================
echo   更新完成！
echo ============================================================
echo.
echo 输出目录: %DIST_DIR%
echo.

REM 显示文件列表
dir /b "%DIST_DIR%\*.exe" "%DIST_DIR%\*.bat" "%DIST_DIR%\*.vbs" 2>nul

pause