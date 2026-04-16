"""测试 get_contact_names"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from wechat_cli.core.contacts import _load_contacts_from

# 使用 cache 解密后的路径
cache_path = r"C:\Users\13658\AppData\Local\Temp\wechat_cli_cache\b8074b9c5a5b.db"

print(f"测试路径: {cache_path}")

if os.path.exists(cache_path):
    names, full = _load_contacts_from(cache_path)
    print(f"联系人总数: {len(names)}")
    
    # 查找 wxid_lliab48hfu9h22
    username = "wxid_lliab48hfu9h22"
    if username in names:
        print(f"\n找到: {username}")
        print(f"  display_name: {names[username]}")
    else:
        print(f"\n没找到: {username}")
        
        # 模糊搜索
        matches = [k for k in names.keys() if 'lliab' in k.lower()]
        if matches:
            print("模糊匹配:")
            for m in matches:
                print(f"  {m}: {names[m]}")
        else:
            print("模糊也没找到")
            
            # 看看 names 里有哪些
            print("\nnames 示例:")
            for k, v in list(names.items())[:10]:
                print(f"  {k}: {v}")
else:
    print("路径不存在")

# 直接 SQL 查询对比
print("\n" + "=" * 50)
print("直接 SQL 查询:")
conn = sqlite3.connect(cache_path)

username = "wxid_lliab48hfu9h22"
row = conn.execute(
    "SELECT username, nick_name, remark FROM contact WHERE username = ?",
    [username]
).fetchone()

if row:
    uname, nick, remark = row
    display = remark if remark else nick if nick else uname
    print(f"SQL 查询:")
    print(f"  username: {uname}")
    print(f"  nick_name: {nick or '(空)'}")
    print(f"  remark: {remark or '(空)'}")
    print(f"  display (计算): {display}")
else:
    print(f"SQL 也没找到: {username}")

conn.close()