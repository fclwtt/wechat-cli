"""查询联系人 - 使用 wechat-cli 解密功能"""
import sys
import os

# 添加 wechat_cli 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import sqlite3
from pathlib import Path
from wechat_cli.core.db_cache import DBCache
from wechat_cli.core.key_utils import strip_key_metadata

# 账号
account = "wxid_ukfuya4wbm9u12_41b3"
accounts_dir = Path.home() / ".wechat-cli" / "accounts"
acc_dir = accounts_dir / account

# 加载密钥
keys_file = acc_dir / "keys.json"
keys_data = json.load(open(keys_file))
all_keys = strip_key_metadata(keys_data)

print(f"密钥数量: {len(all_keys)}")

# db_dir - 从 accounts.json
accounts_json = Path.home() / ".wechat-cli" / "accounts.json"
accounts_data = json.load(open(accounts_json))

# accounts.json 是列表格式，直接是账号名
if isinstance(accounts_data, dict) and "accounts" in accounts_data:
    accounts_list = accounts_data["accounts"]
else:
    accounts_list = accounts_data

# db_dir 需要从其他地方获取
# 微信数据目录格式：D:\WechatMsg\xwechat_files\{account}\db_storage
# 或者从账号名推断 wxid
wxid = account.split('_')[0] if '_' in account else account

# 尝试多个可能的路径
possible_db_dirs = [
    f"D:\\WechatMsg\\xwechat_files\\{account}\\db_storage",
    f"D:\\WechatMsg\\xwechat_files\\{wxid}\\db_storage",
]

db_dir = None
for p in possible_db_dirs:
    if os.path.exists(p):
        db_dir = p
        print(f"db_dir: {db_dir}")
        break

if not db_dir:
    print("未找到 db_dir，请手动指定")
    sys.exit(1)

# 初始化 cache
cache = DBCache(all_keys, db_dir)

# 获取 contact.db
contact_rel = "contact\\contact.db"
contact_path = cache.get(contact_rel)

if contact_path:
    print(f"contact.db 解密后: {contact_path}")
    
    conn = sqlite3.connect(contact_path)
    
    # 查询
    username = "wxid_lliab48hfu9h22"
    try:
        row = conn.execute(
            "SELECT username, nick_name, remark, alias FROM Contact WHERE username = ?",
            [username]
        ).fetchone()
        
        if row:
            uname, nick, remark, alias = row
            print(f"\n{username}:")
            print(f"  nick_name: {nick or '(空)'}")
            print(f"  remark: {remark or '(空)'}")
            print(f"  alias: {alias or '(空)'}")
        else:
            print(f"\n{username} 不在 Contact 表里")
            
            # 模糊搜索
            rows = conn.execute(
                "SELECT username, nick_name, remark FROM Contact WHERE username LIKE '%lliab%' LIMIT 5"
            ).fetchall()
            if rows:
                print("模糊匹配:")
                for r in rows:
                    print(f"  {r[0]}: nick={r[1]}, remark={r[2]}")
            else:
                print("模糊搜索也没找到")
    except Exception as e:
        print(f"查询失败: {e}")
        
        # 看表结构
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        print(f"表: {[t[0] for t in tables]}")
        
        if tables:
            # 看 Contact 表结构
            cols = conn.execute("PRAGMA table_info(Contact)").fetchall()
            print(f"Contact 列: {[c[1] for c in cols]}")
    
    conn.close()
else:
    print("无法解密 contact.db")

# SessionTable
print("\n" + "=" * 50)
session_rel = "session\\session.db"
session_path = cache.get(session_rel)

if session_path:
    print(f"session.db 解密后: {session_path}")
    
    conn = sqlite3.connect(session_path)
    
    username = "wxid_lliab48hfu9h22"
    try:
        cols = conn.execute("PRAGMA table_info(SessionTable)").fetchall()
        col_names = [c[1] for c in cols]
        print(f"SessionTable 列: {col_names}")
        
        row = conn.execute(
            "SELECT * FROM SessionTable WHERE username = ?",
            [username]
        ).fetchone()
        
        if row:
            print(f"\nSessionTable 找到: {username}")
            for name, val in zip(col_names[:10], row[:10]):
                if val:
                    print(f"  {name}: {val}")
        else:
            print(f"{username} 不在 SessionTable 里")
            
            # 显示前 5 个 session
            rows = conn.execute(
                "SELECT username, last_sender_display_name FROM SessionTable LIMIT 5"
            ).fetchall()
            print("SessionTable 示例:")
            for r in rows:
                print(f"  {r[0]}: {r[1] or '(空)'}")
    except Exception as e:
        print(f"查询失败: {e}")
    
    conn.close()
else:
    print("无法解密 session.db")