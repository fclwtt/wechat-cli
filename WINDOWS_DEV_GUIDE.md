# Windows 本地开发指南

## 背景

在 Mac 上构建 Windows exe 需要通过 GitHub Actions，每次修改都要等构建完成才能测试，效率低。

**直接在 Windows 上运行源码，修改立刻生效。**

---

## 1. 系统要求

- Windows 10/11
- Python 3.10+ (推荐 3.12)
- Git

---

## 2. 安装 Python

1. 下载：https://www.python.org/downloads/windows/
   - 选择 Python 3.12.x（最新稳定版）
   - **重要：安装时勾选 "Add Python to PATH"**

2. 验证：
   ```cmd
   python --version
   pip --version
   ```

---

## 3. 克隆源码

```cmd
# 创建工作目录
mkdir E:\dev
cd E:\dev

# 克隆仓库
git clone https://github.com/fclwtt/wechat-cli.git
cd wechat-cli
```

---

## 4. 安装依赖

```cmd
# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate

# 安装项目依赖
pip install -e .
```

---

## 5. 运行命令（无需 exe）

```cmd
# 确保虚拟环境激活
.venv\Scripts\activate

# 初始化（多账号）
python -m wechat_cli init --all

# 导出（带调试信息）
python -m wechat_cli export-all-accounts --debug

# 导出（正常模式）
python -m wechat_cli export-all-accounts --output %USERPROFILE%\wechat-backup --copy-media --limit 2000
```

---

## 6. 调试流程

### 步骤 1：初始化账号

```cmd
python -m wechat_cli init --all
```

**预期输出：**
```
WeChat CLI 多账号初始化
========================================

开始提取所有账号密钥...
[+] 找到微信进程: Weixin.exe (PID: 12345)
[+] 提取密钥...
[+] 解析数据库目录...

[+] 初始化完成!
    账号数: 1
    - wxid_xxx: 12 个密钥
    默认账号: wxid_xxx
    账号目录: C:\Users\你的用户名\.wechat-cli\accounts
```

**如果失败：**
- 确保微信 PC 版正在运行
- 确保已登录微信账号
- 检查是否有杀毒软件拦截进程访问

### 步骤 2：检查账号目录

```cmd
# 查看账号目录结构
dir %USERPROFILE%\.wechat-cli\accounts

# 查看索引文件
type %USERPROFILE%\.wechat-cli\accounts.json
```

**预期结构：**
```
.accounts/
├── wxid_xxx/
│   ├── config.json      ← 账号配置
│   ├── keys.json        ← 密钥文件
│   └── decrypted/       ← 解密缓存
├── wxid_yyy/
│   └── ...
accounts.json             ← 账号索引
```

### 步骤 3：导出（带调试）

```cmd
python -m wechat_cli export-all-accounts --debug
```

**调试输出会显示：**
```
[DEBUG] ACCOUNTS_DIR = C:\Users\xxx\.wechat-cli\accounts
[DEBUG] ACCOUNTS_INDEX_FILE = C:\Users\xxx\.wechat-cli\accounts.json
[DEBUG] accounts index exists = True
[DEBUG] Found accounts: ['wxid_xxx']
```

---

## 7. 修改源码立刻测试

修改任何文件后，直接运行：

```cmd
# 修改了 commands/export_all_accounts.py
python -m wechat_cli export-all-accounts --debug
```

**无需重新构建 exe。**

---

## 8. 常见问题

### Q: `pip install -e .` 报错缺少 Visual C++？

A: 安装 Visual Studio Build Tools：
- 下载：https://visualstudio.microsoft.com/visual-cpp-build-tools/
- 安装时勾选 "C++ build tools"

### Q: `init --all` 报找不到微信进程？

A:
1. 确保微信 PC 版正在运行
2. 检查进程名是否为 `Weixin.exe`（而不是 `WeChatApp.exe`）
3. 杀毒软件可能拦截，临时关闭测试

### Q: `export-all-accounts` 显示 "成功 0"？

A:
1. 先运行 `init --all`
2. 用 `--debug` 查看账号目录是否存在
3. 检查 `accounts.json` 是否有内容

---

## 9. 提交修改到 Git

```cmd
git add .
git commit -m "fix: 修复xxx问题"
git push
```

推送后，Mac 端或其他机器可以 `git pull` 同步。

---

## 10. 快速参考

| 命令 | 说明 |
|------|------|
| `python -m wechat_cli init --all` | 多账号初始化 |
| `python -m wechat_cli export-all-accounts --debug` | 导出（调试模式） |
| `python -m wechat_cli sessions` | 查看会话列表 |
| `dir %USERPROFILE%\.wechat-cli\accounts` | 查看账号目录 |
| `.venv\Scripts\activate` | 激活虚拟环境 |

---

_此文档用于 Windows 本地开发，避免每次修改都要等 GitHub Actions 构建。_