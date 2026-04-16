"""查询联系人 - 简化版"""
import sqlite3
import os
from pathlib import Path

# 从日志里的已知路径
db_dir = r"D:\WechatMsg\xwechat_files\wxid_ukfuya4wbm9u12_41b3\db_storage"
print(f"db_dir: {db_dir}")

# 搜索 contact.db
print("\n搜索 contact.db...")
contact_db = None
for root, dirs, files in os.walk(db_dir):
    for f in files:
        if 'contact' in f.lower() and f.endswith('.db') and '_fts' not in f.lower():
            contact_db = os.path.join(root, f)
            print(f"找到: {contact_db}")
            break
    if contact_db:
        break

if not contact_db:
    print("未找到 contact.db")
else:
    # 尝试读取（可能加密）
    try:
        conn = sqlite3.connect(contact_db)
        
        # 查询表结构
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        print(f"\n表列表: {[t[0] for t in tables[:5]]}")
        
        # 尝试查询 contact 表
        try:
            count = conn.execute("SELECT COUNT(*) FROM Contact").fetchone()[0]
            print(f"联系人总数: {count}")
            
            # 查询特定 username
            username = "wxid_lliab48hfu9h22"
            row = conn.execute(
                "SELECT username, NickName, Remark, Alias FROM Contact WHERE username = ?",
                [username]
            ).fetchone()
            
            if row:
                uname, nick, remark, alias = row
                print(f"\n{username}:")
                print(f"  NickName: {nick or '(空)'}")
                print(f"  Remark: {remark or '(空)'}")
                print(f"  Alias: {alias or '(空)'}")
            else:
                print(f"\n{username} 不在 Contact 表里")
                
                # 模糊搜索
                rows = conn.execute(
                    "SELECT username, NickName, Remark FROM Contact WHERE username LIKE '%lliab%' LIMIT 5"
                ).fetchall()
                if rows:
                    print("模糊匹配:")
                    for r in rows:
                        print(f"  {r[0]}: NickName={r[1]}, Remark={r[2]}")
                        
        except sqlite3.DatabaseError as e:
            print(f"数据库可能加密了: {e}")
            print("（微信数据库是加密的，需要密钥解密后才能读取）")
            
        conn.close()
    except Exception as e:
        print(f"连接失败: {e}")

# 检查 SessionTable
print("\n" + "=" * 50)
print("检查 SessionTable...")
session_db = None
for root, dirs, files in os.walk(db_dir):
    for f in files:
        if 'session' in f.lower() and f.endswith('.db'):
            session_db = os.path.join(root, f)
            print(f"找到: {session_db}")
            break
    if session_db:
        break

if session_db:
    try:
        conn = sqlite3.connect(session_db)
        
        # 查表结构
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        print(f"表: {[t[0] for t in tables]}")
        
        try:
            # 查列名
            cols = conn.execute("PRAGMA table_info(SessionTable)").fetchall()
            print(f"SessionTable 列: {[c[1] for c in cols[:5]]}")
            
            # 尝试查询
            username = "wxid_lliab48hfu9h22"
            try:
                row = conn.execute(
                    "SELECT * FROM SessionTable WHERE username = ?",
                    [username]
                ).fetchone()
                if row:
                    print(f"\nSessionTable 找到: {username}")
                    # 显示前几列
                    col_names = [c[1] for c in cols]
                    for i, (name, val) in enumerate(zip(col_names[:10], row[:10])):
                        print(f"  {name}: {val}")
                else:
                    print(f"{username} 不在 SessionTable 里")
                    
                    # 显示前 5 个 session
                    rows = conn.execute(
                        "SELECT username FROM SessionTable LIMIT 5"
                    ).fetchall()
                    print("\nSessionTable 示例:")
                    for r in rows:
                        print(f"  {r[0]}")
            except Exception as e:
                print(f"查询失败: {e}")
                
        except sqlite3.DatabaseError as e:
            print(f"数据库可能加密: {e}")
            
        conn.close()
    except Exception as e:
        print(f"连接失败: {e}")