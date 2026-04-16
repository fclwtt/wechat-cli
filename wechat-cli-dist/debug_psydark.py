"""检查 psydark 重复问题"""
import sqlite3
import hashlib
import os
from pathlib import Path
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wechat_cli.core.db_cache import DBCache
from wechat_cli.core.key_utils import strip_key_metadata
from wechat_cli.core.contacts import get_contact_names

# 账号
account = "wxid_ukfuya4wbm9u12_41b3"
accounts_dir = Path.home() / ".wechat-cli" / "accounts"
acc_dir = accounts_dir / account

# 加载密钥
keys_data = json.load(open(acc_dir / "keys.json"))
all_keys = strip_key_metadata(keys_data)

# db_dir
accounts_json = Path.home() / ".wechat-cli" / "accounts.json"
accounts_data = json.load(open(accounts_json))

# 推断 db_dir
db_dir = f"D:\\WechatMsg\\xwechat_files\\{account}\\db_storage"

# cache
cache = DBCache(all_keys, db_dir)
decrypted_dir = str(acc_dir / "decrypted")

# 获取联系人
names = get_contact_names(cache, decrypted_dir)
print(f"联系人数量: {len(names)}")

# 构建 hash_to_username
hash_to_username = {}
for uname in names.keys():
    h = hashlib.md5(uname.encode()).hexdigest()
    hash_to_username[h] = uname

# 搜索 psydark 相关
print("\n" + "=" * 50)
print("搜索 display_name 包含 'psydark' 的联系人:")
for uname, display in names.items():
    if 'psydark' in display.lower():
        h = hashlib.md5(uname.encode()).hexdigest()
        print(f"  username: {uname}")
        print(f"  display_name: {display}")
        print(f"  md5 hash: {h}")
        print()

# 找到 Msg 表里有 psydark 消息的
print("=" * 50)
print("从 debug 日志找到的 Msg 表:")
msg_tables_with_psydark = [
    "Msg_93c9ae88ab4c6689d3bdbf1ab88564bd",  # 24 条消息
    "Msg_67b88244bcc39cf830e2d7e06c1d37ce",  # 102 条消息
]

for table_name in msg_tables_with_psydark:
    table_hash = table_name.replace('Msg_', '')
    chat_username = hash_to_username.get(table_hash)
    
    print(f"\n{table_name}:")
    print(f"  hash: {table_hash}")
    if chat_username:
        print(f"  匹配到 username: {chat_username}")
        print(f"  display_name: {names.get(chat_username, chat_username)}")
    else:
        print(f"  未匹配到 username (可能是 unknown_{table_hash})")

print("\n" + "=" * 50)
print("结论:")
print("如果两个 Msg 表匹配到同一个 username，说明去重逻辑应该合并它们")
print("如果匹配到不同 username，说明是两个不同群聊（同名）")