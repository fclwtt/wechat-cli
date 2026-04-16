# wechat-cli-dist 分发文件夹

这个文件夹包含所有需要分发的文件，可以直接打包给其他电脑使用。

## 文件列表

| 文件 | 说明 |
|------|------|
| wechat-cli.exe | 主程序（需要构建） |
| init.bat | 初始化账号密钥（双击运行） |
| export-all-accounts.bat | 全量导出（显示窗口） |
| export-all-silent.vbs | 全量导出（隙执行，完成后弹窗） |
| export-daily-silent.vbs | 每日导出（隙执行，完成后弹窗） |
| update-dist.bat | 一键更新（拉取 + 构建） |

## 使用方式

### 首次使用
```cmd
双击 init.bat
```

### 全量导出（所有聊天）
```cmd
双击 export-all-silent.vbs
```

### 每日导出（昨天有新消息的聊天）
```cmd
双击 export-daily-silent.vbs
```

### 设置定时任务（每天自动导出）
```cmd
schtasks /create /tn "WeChatDailyExport" /tr "E:\wechat-cli-build\wechat-cli\wechat-cli-dist\export-daily-silent.vbs" /sc daily /st 10:30 /rl HIGHEST /f
```

## 输出目录
- 默认: C:\Users\13658\wechat-chats-backup
- 每日索引: daily-index\YYYY-MM-DD.txt（记录更新的聊天）

## 更新
```cmd
双击 update-dist.bat
```

## 日志文件
- export-daily-log.txt: 每日导出日志
- export-all-log.txt: 全量导出日志

## 注意事项
1. 微信必须保持登录状态（后台运行即可）
2. 首次运行会解密数据库（慢），后续运行复用缓存（快）
3. 定时任务需要电脑开机才能执行