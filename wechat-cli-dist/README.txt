# wechat-cli-dist 分发文件夹

这个文件夹包含所有需要分发的文件，可以直接打包给其他电脑使用。

## 文件列表

| 文件 | 说明 |
|------|------|
| wechat-cli.exe | 主程序（需要构建） |
| init.bat | 初始化账号密钥 |
| export-all-accounts.bat | 导出所有账号全部聊天记录 |
| export-daily-html.bat | 每日增量导出（显示窗口） |
| export-daily-html-hidden.bat | 每日增量导出（隐藏窗口） |
| export-daily-html-silent.vbs | 双击后台执行，完成后弹窗提示 |
| setup-scheduled-task.ps1 | 创建 Windows 定时任务 |
| update-dist.bat | 一键更新（拉取源码 + 构建） |

## 使用方式

### 本机更新
```cmd
cd E:\wechat-cli-build\wechat-cli\wechat-cli-dist
update-dist.bat
```

### 分发给别人
直接打包整个 `wechat-cli-dist` 文件夹即可（exe 需要 building）。

## 输出目录
- 默认: E:\wechat-chats-backup
- 每日索引: E:\wechat-chats-backup\daily-index\YYYY-MM-DD.txt