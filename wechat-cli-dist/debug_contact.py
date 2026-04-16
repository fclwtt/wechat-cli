"""查询联系人 - 直接从数据库查询"""
import sqlite3
import json
import os
from pathlib import Path

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

# 加载 accounts.json
accounts_json = Path.home() / ".wechat-cli" / "accounts.json"
accounts_data = json.load(open(accounts_json))

# accounts.json 可能是列表或字典
if isinstance(accounts_data, list):
    # 列表格式：直接包含账号名
    accounts_list = accounts_data
    print(f"账号列表: {accounts_list}")
else:
    # 字典格式
    accounts_list = accounts_data.get("accounts", [])
    print(f"账号列表: {accounts_list}")

# db_dir 从账号名推断
# 微信数据目录在 D:\WechatMsg\xwechat_files\
wxid_part = account.split('_')[0] if '_' in account else account
possible_db_dirs = [
    f"D:\\WechatMsg\\xwechat_files\\{account}\\db_storage",
    f"D:\\WechatMsg\\xwechat_files\\{wxid_part}\\db_storage",
]

db_dir = None
for p in possible_db_dirs:
    if os.path.exists(p):
        db_dir = p
        break

print(f"db_dir: {db_dir}")

# 查找 contact.db（加密的）
contact_db_path = None
if db_dir:
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if 'contact' in f.lower() and f.endswith('.db') and not f.endswith('_fts.db'):
                contact_db_path = os.path.join(root, f)
                print(f"找到加密 contact.db: {contact_db_path}")
                break
        if contact_db_path:
            break

# 检查 decrypted 目录（预解密的）
decrypted_dir = acc_dir / "decrypted"
if decrypted_dir.exists():
    for root, dirs, files in os.walk(str(decrypted_dir)):
        for f in files:
            if 'contact' in f.lower() and f.endswith('.db') and not f.endswith('_fts.db'):
                contact_db_path = os.path.join(root, f)
                print(f"使用预解密: {contact_db_path}")
                break
        if contact_db_path:
            break

if not contact_db_path:
    print("未找到 contact.db")
else:
    print(f"\n查询: {contact_db_path}")
    
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
                
                # 嘗试模糊搜索
                rows = conn.execute(
                    "SELECT username, nick_name, remark, alias FROM contact WHERE username LIKE '%lliab%'"
                ).fetchall()
                if rows:
                    print(f"模糊匹配:")
                    for r in rows:
                        print(f"  {r}")
        except Exception as e:
            print(f"查询失败: {e}")
            # 可能加密或表结构不同
            try:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                print(f"表列表: {[t[0] for t in tables]}")
            except:
                print("数据库可能加密了，无法读取")
            
        conn.close()
    except Exception as e:
        print(f"连接失败: {e}")

# 检查 SessionTable
print("\n" + "=" * 50)
print("检查 SessionTable...")
session_db_path = None
if db_dir:
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if 'session' in f.lower() and f.endswith('.db'):
                session_db_path = os.path.join(root, f)
                break
        if session_db_path:
            break

if not session_db_path:
    # 也可能在 decrypted 目录
    if decrypted_dir.exists():
        for root, dirs, files in os.walk(str(decrypted_dir)):
            for f in files:
                if 'session' in f.lower() and f.endswith('.db'):
                    session_db_path = os.path.join(root, f)
                    break

if session_db_path:
    print(f"找到 session.db: {session_db_path}")
    try:
        conn = sqlite3.connect(session_db_path)
        
        username = "wxid_lliab48hfu9h22"
        try:
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
                
                # 列出所有 SessionTable 条目（前10个）
                rows = conn.execute(
                    "SELECT username, last_sender_display_name FROM SessionTable LIMIT 10"
                ).fetchall()
                print("\nSessionTable 示例:")
                for uname, display in rows:
                    print(f"  {uname}: {display or '(空)'}")
        except Exception as e:
            print(f"查询失败: {e}")
            
        conn.close()
    except Exception as e:
        print(f"连接失败: {e}")
else:
    print("未找到 session.db")