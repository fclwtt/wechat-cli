# 微信聊天每日导出定时任务设置脚本
# 使用方法：右键 → 使用 PowerShell 运行

$taskName = "微信聊天每日导出"
$batPath = "$PSScriptRoot\export-daily-html.bat"
$workDir = $PSScriptRoot
$runTime = "09:00"  # 每天 9 点执行

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  微信聊天每日导出定时任务设置" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 检查 bat 文件是否存在
if (-not (Test-Path $batPath)) {
    Write-Host "[错误] 找不到 export-daily-html.bat" -ForegroundColor Red
    Write-Host "请确保此脚本和 export-daily-html.bat 在同一目录" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

Write-Host "任务名称：$taskName"
Write-Host "执行时间：每天 $runTime"
Write-Host "脚本路径：$batPath"
Write-Host "工作目录：$workDir"
Write-Host ""

# 删除已有任务（如果存在）
$existingTask = Get-ScheduledTask -TaskName "$taskName" -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "删除已有任务..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName "$taskName" -Confirm:$false
}

Write-Host "创建定时任务..." -ForegroundColor Green

# 创建触发器（每天指定时间执行）
$trigger = New-ScheduledTaskTrigger -Daily -At $runTime

# 创建操作（执行 bat 文件）
$action = New-ScheduledTaskAction -Execute "$batPath" -WorkingDirectory "$workDir"

# 创建设置
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfDontStopOnIdleEnd `
    -RunOnlyIfNetworkAvailable:$false `
    -WakeToRun:$false `
    -DontStopIfGoingOnBatteries `
    -StartIfOnBatteries

# 注册任务（最高权限运行）
Register-ScheduledTask `
    -TaskName "$taskName" `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  定时任务已创建成功！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# 显示任务详情
Write-Host "任务详情：" -ForegroundColor Cyan
Get-ScheduledTask -TaskName "$taskName" | Select-Object TaskName, State, LastRunTime, NextRunTime | Format-Table

Write-Host ""
Write-Host "立即测试任务..." -ForegroundColor Yellow
schtasks /run /tn "$taskName"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "注意事项：" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "1. 微信必须保持登录状态（后台运行即可）"
Write-Host "2. 电脑必须开机才能执行定时任务"
Write-Host "3. 每天执行时间：$runTime"
Write-Host "4. 输出目录：C:\Users\<用户名>\wechat-chats-backup\"
Write-Host ""
Write-Host "修改执行时间：" -ForegroundColor Yellow
Write-Host "  任务计划程序 → 找到任务 → 属性 → 触发器 → 编辑"
Write-Host ""
Write-Host "删除定时任务：" -ForegroundColor Yellow
Write-Host "  schtasks /delete /tn '$taskName' /f"
Write-Host ""

pause