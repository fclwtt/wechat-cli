#!/usr/bin/env python3
"""
Windows exe 打包脚本

使用方法（在 Windows 上运行）：
1. pip install pyinstaller
2. python build_windows.py
3. 生成的 exe 在 dist/wechat-cli.exe
"""

import os
import sys
import shutil
import subprocess

# 确保在项目根目录运行
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print("=" * 60)
print("  wechat-cli Windows exe 打包")
print("=" * 60)

# 1. 清理旧文件
print("\n[1/4] 清理旧构建文件...")
for d in ["build", "dist", "__pycache__"]:
    if os.path.exists(d):
        shutil.rmtree(d)
        print(f"  删除: {d}")

# 2. 确保 PyInstaller 已安装
print("\n[2/4] 检查 PyInstaller...")
try:
    import PyInstaller
    print("  PyInstaller 已安装")
except ImportError:
    print("  安装 PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

# 3. 创建 spec 文件（更好的控制）
print("\n[3/4] 创建 spec 文件...")
spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['wechat_cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'wechat_cli',
        'wechat_cli.main',
        'wechat_cli.core',
        'wechat_cli.core.config',
        'wechat_cli.core.context',
        'wechat_cli.core.crypto',
        'wechat_cli.core.messages',
        'wechat_cli.core.contacts',
        'wechat_cli.core.db_cache',
        'wechat_cli.core.key_utils',
        'wechat_cli.keys',
        'wechat_cli.keys.scanner_windows',
        'wechat_cli.keys.common',
        'wechat_cli.commands',
        'wechat_cli.commands.init',
        'wechat_cli.commands.sessions',
        'wechat_cli.commands.history',
        'wechat_cli.commands.search',
        'wechat_cli.commands.contacts',
        'wechat_cli.commands.new_messages',
        'wechat_cli.commands.members',
        'wechat_cli.commands.export',
        'wechat_cli.commands.stats',
        'wechat_cli.commands.unread',
        'wechat_cli.commands.favorites',
        'wechat_cli.output',
        'Crypto',
        'Crypto.Cipher',
        'Crypto.Cipher.AES',
        'zstandard',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'wechat_cli.keys.scanner_macos',
        'wechat_cli.keys.scanner_linux',
        'PyObjCTools',
        'objc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wechat-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

with open("wechat-cli.spec", "w", encoding="utf-8") as f:
    f.write(spec_content)
print("  创建: wechat-cli.spec")

# 4. 运行 PyInstaller
print("\n[4/4] 运行 PyInstaller...")
result = subprocess.run(
    [sys.executable, "-m", "PyInstaller", "--clean", "wechat-cli.spec"],
    check=False
)

if result.returncode == 0:
    exe_path = os.path.join("dist", "wechat-cli.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / 1024 / 1024
        print("\n" + "=" * 60)
        print("  打包成功!")
        print("=" * 60)
        print(f"\n  输出: {os.path.abspath(exe_path)}")
        print(f"  大小: {size_mb:.1f} MB")
        print("\n使用方法:")
        print("  wechat-cli.exe init          # 初始化")
        print("  wechat-cli.exe sessions     # 查看会话")
        print("  wechat-cli.exe history \"张三\"  # 查看聊天记录")
    else:
        print("\n[!] 未找到输出文件")
        sys.exit(1)
else:
    print("\n[!] PyInstaller 失败")
    sys.exit(1)