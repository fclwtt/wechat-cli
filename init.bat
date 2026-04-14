@echo off
chcp 65001 >nul
title 微信聊天记录初始化

echo.
echo ============================================
echo   微信聊天记录导出工具 - 初始化
echo ============================================
echo.
echo 此脚本将：
echo   1. 检测微信进程
echo   2. 提取解密密钥
echo   3. 保存账号配置
echo.
echo 请确保：
echo   - 微信已登录（多账号需同时登录）
echo   - 微信窗口保持打开状态
echo.
echo ============================================
echo.

pause

echo.
echo [开始初始化]
echo.

wechat-cli.exe init --all

echo.
echo ============================================
echo   初始化完成！
echo ============================================
echo.
echo 下一步：
echo   1. 双击 export-all-html.bat 导出所有聊天
echo   2. 双击 export-daily-html.bat 每日增量导出
echo.

pause