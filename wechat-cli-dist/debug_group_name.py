"""检查群聊名字获取问题"""
import sqlite3
import hashlib
import os
from pathlib import Path
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wechat_cli.core.db_cache import DBCache
from wechat_cli.core.key_utils import strip_key_metadata

# 账号
account = "wxid_ukfuya4wbm9u12_41b3"
acc_dir = Path.home() / ".wechat-cli" / "accounts" / account
keys_data = json.load(open(acc_dir / "keys.json"))
all_keys = strip_key_metadata(keys_data)

db_dir = f"D:\\WechatMsg\\xwechat_files\\{account}\\db_storage"
cache = DBCache(all_keys, db_dir)
decrypted_dir = str(acc_dir / "decrypted")

# 两个群的 Msg 表 hash
msg_hashes = [
    "93c9ae88ab4c6689d3bdbf1ab88564bd",
    "67b88244bcc39cf830e2d7e06c1d37ce",
]

# 解密 contact.db
contact_path = cache.get("contact\\contact.db")
print(f"contact.db: {contact_path}")

conn = sqlite3.connect(contact_path)

print("\n" + "=" * 50)
print("检查群聊名获取逻辑")

for msg_hash in msg_hashes:
    print(f"\nMsg 表 hash: {msg_hash}")
    
    # 尝试反查 username
    # 微信 Msg 表名是 Msg_<MD5(username)>
    # 需要在 contact 表里找
    
    # 方案1: 遍历所有 username 计算 MD5 匹配
    rows = conn.execute(
        "SELECT username, nick_name, remark FROM contact WHERE username LIKE '%@chatroom'"
    ).fetchall()
    
    matched = None
    for uname, nick, remark in rows:
        h = hashlib.md5(uname.encode()).hexdigest()
        if h == msg_hash:
            matched = (uname, nick, remark)
            break
    
    if matched:
        uname, nick, remark = matched
        print(f"  匹配到群聊:")
        print(f"    username: {uname}")
        print(f"    nick_name: {nick or '(空)'}")
        print(f"    remark: {remark or '(空)'}")
        
        # 显示名逻辑：remark > nick > username
        display = remark if remark else nick if nick else uname
        print(f"    display_name (计算): {display}")
        
        # 检查为什么显示 psydark
        print(f"\n  问题排查:")
        if not remark and not nick:
            print(f"    群名 nick_name 和 remark 都是空!")
            print(f"    可能原因: contact 表里这条记录不完整")
            
            # 查看完整记录
            full_row = conn.execute(
                "SELECT * FROM contact WHERE username = ?",
                [uname]
            ).fetchone()
            if full_row:
                cols = [d[0] for d in conn.execute("PRAGMA table_info(contact)").fetchall()]
                print(f"    完整记录:")
                for i, c in enumerate(cols[:15]):
                    if full_row[i]:
                        print(f"      {c}: {full_row[i][:50] if isinstance(full_row[i], str) else full_row[i]}")
    else:
        print(f"  未匹配到群聊 username")
        print(f"  可能原因: hash_to_username 映射来源不对")
        
        # 检查 names 字典是怎么构建的
        print(f"\n  检查 names 字典来源:")
        
        # 从 contact 表构建
        rows = conn.execute(
            "SELECT username, nick_name, remark FROM contact"
        ).fetchall()
        
        for uname, nick, remark in rows:
            h = hashlib.md5(uname.encode()).hexdigest()
            if h == msg_hash:
                print(f"    找到匹配: {uname}")
                print(f"    nick_name: {nick}")
                print(f"    remark: {remark}")
                break

conn.close()

print("\n" + "=" * 50)
print("检查 SessionTable 是否有群名")

session_path = cache.get("session\\session.db")
if session_path:
    conn2 = sqlite3.connect(session_path)
    
    cols = conn2.execute("PRAGMA table_info(SessionTable)").fetchall()
    print(f"SessionTable 列: {[c[1] for c in cols]}")
    
    # 检查是否有 last_sender_display_name 列存群名
    for msg_hash in msg_hashes:
        # 需要先找到 username
        pass
    
    conn2.close()