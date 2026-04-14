import re

with open('wechat_cli/commands/export_all_accounts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到并替换
old_text = '''            # 创建聊天目录
            safe_name = chat_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            chat_dir = account_dir / safe_name
            chat_dir.mkdir(parents=True, exist_ok=True)'''

new_text = '''            # 创建聊天目录
            folder_name = chat_info['display_name'] or chat_info['username']
            # 如果 display_name 是表名(Msg_xxx)，用 username
            if folder_name.startswith('Msg_'):
                folder_name = chat_info['username'] if not chat_info['username'].startswith('Msg_') else folder_name
            safe_name = folder_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            chat_dir = account_dir / safe_name
            chat_dir.mkdir(parents=True, exist_ok=True)'''

content = content.replace(old_text, new_text)

with open('wechat_cli/commands/export_all_accounts.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("已修复")