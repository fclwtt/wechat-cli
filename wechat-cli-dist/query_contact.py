"""查询联系人 - 简单脚本"""
import sqlite3
import os
from pathlib import Path

# 账号目录
account = "wxid_ukfuya4wbm9u12_41b3"
accounts_dir = Path.home() / ".wechat-cli" / "accounts"
acc_dir = accounts_dir / account

# 查找 contact.db
# 可能位置：
# 1. decrypted/contact/contact.db (预解密)
# 2. 直接从 cache 获取（需要 keys）

decrypted_contact = acc_dir / "decrypted" / "contact" / "contact.db"
if decrypted_contact.exists():
    print(f"使用预解密: {decrypted_contact}")
    db_path = str(decrypted_contact)
else:
    print("预解密文件不存在，需要在线解密")
    print("请先运行完整导出一次（export-all-accounts），会自动解密 contact.db")
    exit(1)

# 查询
conn = sqlite3.connect(db_path)

# 查询特定 username
username = "wxid_lliab48hfu9h22"
row = conn.execute(
    "SELECT username, nick_name, remark, alias FROM contact WHERE username = ?",
    [username]
).fetchone()

if row:
    uname, nick, remark, alias = row
    print(f"\n联系人信息:")
    print(f"  username: {uname}")
    print(f"  nick_name: {nick or '(空)'}")
    print(f"  remark: {remark or '(空)'}")
    print(f"  alias (微信号): {alias or '(空)'}")
else:
    print(f"\n未找到: {username}")
    print("这个联系人不在 contact.db 里（可能是陌生人或已删除）")

# 统计
count = conn.execute("SELECT COUNT(*) FROM contact").fetchone()[0]
print(f"\n联系人总数: {count}")

conn.close()