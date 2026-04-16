"""查询联系人 - 直接从数据库查询"""
import sqlite3
import json
import os
from pathlib import Path
import hashlib

# 账号
account = "wxid_ukfuya4wbm9u12_41b3"
accounts_dir = Path.home() / ".wechat-cli" / "accounts"
acc_dir = accounts_dir / account
keys_file = acc_dir / "keys.json"

# 加载密钥
keys_data = json.load(open(keys_file))
print(f"密钥数量: {len(keys_data)}")

# 找到 contact 相关的密钥
contact_keys = [k for k in keys_data if 'contact' in k.lower()]
print(f"contact 密钥: {contact_keys}")

if not contact_keys:
    print("未找到 contact 密钥")
    # 尝试找 MicroMsg.db 里的 contact 信息
    micromsg_keys = [k for k in keys_data if 'micromsg' in k.lower()]
    print(f"MicroMsg 密钥: {micromsg_keys}")

# 加载 accounts.json 获取 db_dir
accounts_json = Path.home() / ".wechat-cli" / "accounts.json"
accounts_data = json.load(open(accounts_json))
acc_info = accounts_data.get("accounts_info", {}).get(account, {})
db_dir = acc_info.get("db_dir")
print(f"db_dir: {db_dir}")

# 查找 contact.db
contact_db_path = None
if db_dir:
    # 尝试常见路径
    possible_paths = [
        os.path.join(db_dir, "contact", "contact.db"),
        os.path.join(db_dir, "Contact", "contact.db"),
        os.path.join(db_dir, "misc", "contact.db"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            contact_db_path = p
            break

if not contact_db_path:
    # 递归搜索
    print("搜索 contact.db...")
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if 'contact' in f.lower() and f.endswith('.db'):
                contact_db_path = os.path.join(root, f)
                print(f"找到: {contact_db_path}")
                break
        if contact_db_path:
            break

# 解密（使用 pysqlcipher3 或 sqlcipher）
# 这里用 Python 的 sqlcipher 库
try:
    from sqlcipher3 import dbapi2 as sqlite
except ImportError:
    print("sqlcipher3 未安装，尝试用标准 sqlite3（不解密）")
    sqlite = sqlite3
    
    # 如果 db 加密，会失败
    # 让用户手动找解密后的文件
    
    # 检查 decrypted 目录
    decrypted_dir = acc_dir / "decrypted"
    if decrypted_dir.exists():
        for root, dirs, files in os.walk(str(decrypted_dir)):
            for f in files:
                if 'contact' in f.lower() and f.endswith('.db'):
                    contact_db_path = os.path.join(root, f)
                    print(f"使用预解密: {contact_db_path}")
                    break
            if contact_db_path:
                break

if contact_db_path:
    print(f"\n查询: {contact_db_path}")
    
    # 尝试连接
    try:
        conn = sqlite3.connect(contact_db_path)
        
        # 查询 wxid_lliab48hfu9h22
        username = "wxid_lliab48hfu9h22"
        try:
            row = conn.execute(
                "SELECT username, nick_name, remark, alias FROM contact WHERE username = ?",
                [username]
            ).fetchone()
            
            if row:
                uname, nick, remark, alias = row
                print(f"\n联系人: {username}")
                print(f"  nick_name: {nick or '(空)'}")
                print(f"  remark: {remark or '(空)'}")
                print(f"  alias: {alias or '(空)'}")
            else:
                print(f"\n{username} 不在 contact 表里")
                
                # 尗试模糊搜索
                rows = conn.execute(
                    "SELECT username, nick_name, remark, alias FROM contact WHERE username LIKE '%lliab%'"
                ).fetchall()
                if rows:
                    print(f"模糊匹配:")
                    for r in rows:
                        print(f"  {r}")
                else:
                    print("模糊搜索也没找到")
        except Exception as e:
            print(f"查询失败: {e}")
            # 可能表结构不同
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            print(f"表列表: {[t[0] for t in tables]}")
            
        conn.close()
    except Exception as e:
        print(f"连接失败（可能加密）: {e}")
else:
    print("未找到 contact.db")

# 另一个来源：SessionTable
print("\n" + "=" * 50)
print("检查 SessionTable...")
session_db_path = None
if db_dir:
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if 'session' in f.lower() and f.endswith('.db'):
                session_db_path = os.path.join(root, f)
                print(f"找到 session.db: {session_db_path}")
                break
        if session_db_path:
            break

if session_db_path:
    try:
        conn = sqlite3.connect(session_db_path)
        # 查询 SessionTable
        row = conn.execute(
            "SELECT username, last_sender_display_name FROM SessionTable WHERE username = ?",
            [username]
        ).fetchone()
        
        if row:
            uname, display_name = row
            print(f"\nSessionTable: {username}")
            print(f"  last_sender_display_name: {display_name or '(空)'}")
        else:
            print(f"{username} 不在 SessionTable 里")
        conn.close()
    except Exception as e:
        print(f"查询失败: {e}")