"""检查无名群聊的识别问题"""
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
decrypted_dir = str(acc_dir / "decrypted")
cache = DBCache(all_keys, db_dir, decrypted_dir)

# 目标群聊
chatroom = "57545224421@chatroom"
print(f"检查群聊: {chatroom}")

# 1. 检查 contact.db
print("\n" + "=" * 50)
print("检查 contact.db")
contact_path = cache.get("contact\\contact.db")
conn = sqlite3.connect(contact_path)

row = conn.execute(
    "SELECT username, nick_name, remark, local_type FROM contact WHERE username = ?",
    [chatroom]
).fetchone()

if row:
    uname, nick, remark, local_type = row
    print(f"找到群聊:")
    print(f"  username: {uname}")
    print(f"  nick_name: {nick or '(空)'}")
    print(f"  remark: {remark or '(空)'}")
    print(f"  local_type: {local_type}")
    
    # 检查完整记录
    full_row = conn.execute("SELECT * FROM contact WHERE username = ?", [chatroom]).fetchone()
    cols = [d[0] for d in conn.execute("PRAGMA table_info(contact)").fetchall()]
    print(f"\n完整记录:")
    for i, c in enumerate(cols):
        if full_row[i]:
            print(f"  {c}: {str(full_row[i])[:100]}")
    
    # 尝试获取群成员
    print(f"\n群成员:")
    try:
        # 找到 contact.id
        id_row = conn.execute("SELECT id FROM contact WHERE username = ?", [chatroom]).fetchone()
        if id_row:
            room_id = id_row[0]
            members = conn.execute(
                "SELECT member_id FROM chatroom_member WHERE room_id = ?",
                [room_id]
            ).fetchall()
            print(f"  成员数: {len(members)}")
            
            # 获取成员昵称
            if members:
                member_ids = [m[0] for m in members]
                placeholders = ','.join('?' * len(member_ids))
                member_info = conn.execute(
                    f"SELECT id, username, nick_name, remark FROM contact WHERE id IN ({placeholders})",
                    member_ids
                ).fetchall()
                
                # 组合群名
                member_names = []
                for uid, username, nick, remark in member_info[:5]:  # 前5个成员
                    display = remark or nick or username
                    member_names.append(display)
                
                combined_name = "、".join(member_names)
                print(f"  群成员昵称组合: {combined_name}")
                print(f"  建议群名: {combined_name} ({len(members)}人)")
    except Exception as e:
        print(f"  查询群成员失败: {e}")
else:
    print(f"未找到: {chatroom}")

conn.close()

# 2. 检查 SessionTable
print("\n" + "=" * 50)
print("检查 SessionTable")
session_path = cache.get("session\\session.db")
conn2 = sqlite3.connect(session_path)

cols = conn2.execute("PRAGMA table_info(SessionTable)").fetchall()
print(f"SessionTable 列: {[c[1] for c in cols[:20]]}")

row = conn2.execute(
    "SELECT * FROM SessionTable WHERE username = ?",
    [chatroom]
).fetchone()

if row:
    col_names = [c[1] for c in cols]
    print(f"\nSessionTable 找到: {chatroom}")
    for name, val in zip(col_names[:15], row[:15]):
        if val:
            print(f"  {name}: {str(val)[:100]}")
else:
    print(f"SessionTable 未找到: {chatroom}")

conn2.close()

# 3. 计算 Msg 表 hash
print("\n" + "=" * 50)
print("Msg 表映射")
msg_hash = hashlib.md5(chatroom.encode()).hexdigest()
print(f"  chatroom username: {chatroom}")
print(f"  MD5 hash: {msg_hash}")
print(f"  Msg 表名应为: Msg_{msg_hash}")