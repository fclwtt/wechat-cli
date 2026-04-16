@echo off
chcp 65001 >nul
title Update wechat-cli-dist

echo ============================================================
echo   wechat-cli-dist 一键更新
echo ============================================================
echo.

REM 设置源码目录（上一级，仓库根目录）
set SOURCE_DIR=%~dp0..
set DIST_DIR=%~dp0

echo 源码目录: %SOURCE_DIR%
echo 输出目录: %DIST_DIR%
echo.

REM 检查源码目录是否存在
if not exist "%SOURCE_DIR%" (
    echo [错误] 源码目录不存在: %SOURCE_DIR%
    pause
    exit /b 1
)

REM 1. 拉取最新源码
echo [1/2] 拉取最新源码...
cd /d "%SOURCE_DIR%"
git pull
if errorlevel 1 (
    echo [警告] git pull 失败，继续构建...
)
echo.

REM 2. 构建 exe
echo [2/2] 构建 exe...
python build_windows.py
if errorlevel 1 (
    echo [错误] 构建失败
    pause
    exit /b 1
)
echo.

REM 3. 复制 exe 到当前目录
copy /y "%SOURCE_DIR%\dist\wechat-cli.exe" "%DIST_DIR%\wechat-cli.exe" >nul
echo 已复制: wechat-cli.exe

echo.
echo ============================================================
echo   更新完成！
echo ============================================================
echo.
echo 分发文件夹: %DIST_DIR%
echo.
echo 文件列表:
dir /b "%DIST_DIR%\*.exe" "%DIST_DIR%\*.bat" "%DIST_DIR%\*.vbs" "%DIST_DIR%\*.ps1" 2>nul

pause