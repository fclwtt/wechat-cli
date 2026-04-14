"""export-html 命令 - 导出聊天记录为美观的 HTML 页面（纯文字版）"""

import click
import os
from datetime import datetime
from pathlib import Path

from ..core.contacts import get_contact_names
from ..core.messages import (
    collect_chat_history,
    parse_time_range,
    resolve_chat_context,
    validate_pagination,
    _iter_table_contexts,
    _query_messages,
    _parse_message_content,
    _split_msg_type,
)


@click.command("export-html")
@click.argument("chat_name")
@click.option("--output", "output_path", default=None, help="输出目录路径(默认当前目录)")
@click.option("--start-time", default="", help="起始时间 YYYY-MM-DD [HH:MM[:SS]]")
@click.option("--end-time", default="", help="结束时间 YYYY-MM-DD [HH:MM[:SS]]")
@click.option("--limit", default=2000, help="导出消息数量")
@click.pass_context
def export_html(ctx, chat_name, output_path, start_time, end_time, limit):
    """导出聊天记录为美观的 HTML 页面（纯文字版）

    \b
    示例:
      wechat-cli export-html "张三"
      wechat-cli export-html "工作群" --output D:\\backup\\chats
      wechat-cli export-html "张三" --start-time "2026-04-01"
    """
    app = ctx.obj

    try:
        validate_pagination(limit, 0, limit_max=None)
        start_ts, end_ts = parse_time_range(start_time, end_time)
    except ValueError as e:
        click.echo(f"错误: {e}", err=True)
        ctx.exit(2)

    chat_ctx = resolve_chat_context(chat_name, app.msg_db_keys, app.cache, app.decrypted_dir)
    if not chat_ctx:
        click.echo(f"找不到聊天对象: {chat_name}", err=True)
        ctx.exit(1)
    if not chat_ctx['db_path']:
        click.echo(f"找不到 {chat_ctx['display_name']} 的消息记录", err=True)
        ctx.exit(1)

    names = get_contact_names(app.cache, app.decrypted_dir)
    
    # 直接使用已有的 collect_chat_history 函数
    lines, failures = collect_chat_history(
        chat_ctx, names, app.display_name_fn,
        start_ts=start_ts, end_ts=end_ts, limit=limit, offset=0,
    )

    if not lines:
        click.echo(f"{chat_ctx['display_name']} 无消息记录", err=True)
        ctx.exit(0)

    # 确定输出目录
    if output_path:
        out_dir = Path(output_path)
    else:
        out_dir = Path.cwd() / "wechat-chats"

    # 创建目录
    safe_name = chat_ctx['display_name'].replace('/', '_').replace('\\', '_').replace(':', '_')
    html_dir = out_dir / safe_name
    html_dir.mkdir(parents=True, exist_ok=True)

    # 转换 lines 为 messages 格式
    messages = []
    for line in lines:
        # line 格式: "时间 发送者: 内容"
        # 解析时间、发送者、内容
        parts = line.split(' ', 2)
        if len(parts) >= 3:
            time_str = parts[0]
            rest = parts[1] + ' ' + parts[2]
            # 发送者: 内容
            if ': ' in rest:
                sender_part, content = rest.split(': ', 1)
                is_self = sender_part == '我'
            else:
                sender_part = rest
                content = ''
                is_self = False
        else:
            time_str = parts[0] if parts else ''
            sender_part = ''
            content = line
            is_self = False
        
        messages.append({
            'time': time_str,
            'sender': sender_part,
            'content': content,
            'is_self': is_self,
        })

    # 生成 HTML
    html_content = _generate_html(
        chat_ctx['display_name'],
        chat_ctx['is_group'],
        start_time or "最早",
        end_time or "最新",
        messages,
    )

    # 写入 HTML 文件
    html_file = html_dir / "index.html"
    html_file.write_text(html_content, encoding='utf-8')

    # 生成 Markdown
    md_content = _generate_markdown(
        chat_ctx['display_name'],
        chat_ctx['is_group'],
        start_time or "最早",
        end_time or "最新",
        messages,
    )

    # 写入 Markdown 文件
    md_file = html_dir / "index.md"
    md_file.write_text(md_content, encoding='utf-8')

    click.echo(f"已导出: {html_file}")
    click.echo(f"Markdown: {md_file}")
    click.echo(f"消息数: {len(messages)}")


def _generate_html(display_name, is_group, start_time, end_time, messages):
    """生成美观的 HTML 页面"""

    chat_type = "群聊" if is_group else "私聊"
    msg_count = len(messages)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>聊天记录 - {display_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}

        .header .meta {{
            font-size: 14px;
            opacity: 0.9;
        }}

        .stats {{
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}

        .stat-item {{
            text-align: center;
        }}

        .stat-item .number {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-item .label {{
            font-size: 12px;
            color: #6c757d;
            margin-top: 4px;
        }}

        .chat-container {{
            max-height: 800px;
            overflow-y: auto;
            padding: 20px;
        }}

        .message {{
            margin-bottom: 16px;
            clear: both;
        }}

        .message.self {{
            text-align: right;
        }}

        .message.other {{
            text-align: left;
        }}

        .message.system {{
            text-align: center;
            color: #6c757d;
            font-size: 12px;
        }}

        .message-header {{
            display: inline-block;
            margin-bottom: 4px;
        }}

        .sender {{
            font-size: 12px;
            color: #6c757d;
            margin-right: 8px;
        }}

        .time {{
            font-size: 11px;
            color: #adb5bd;
        }}

        .message-body {{
            display: inline-block;
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 12px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }}

        .message.self .message-body {{
            background: #667eea;
            color: white;
        }}

        .message.other .message-body {{
            background: #f1f3f4;
            color: #202124;
        }}

        .message.system .message-body {{
            background: transparent;
            padding: 4px 8px;
        }}

        .footer {{
            padding: 20px;
            background: #f8f9fa;
            text-align: center;
            font-size: 12px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{display_name}</h1>
            <div class="meta">
                {chat_type} · {start_time} 至 {end_time}
            </div>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="number">{msg_count}</div>
                <div class="label">消息总数</div>
            </div>
        </div>

        <div class="chat-container">
'''

    # 添加消息
    for msg in messages:
        msg_class = "self" if msg['is_self'] else "other"
        content_html = msg['content']

        # 转义 HTML 特殊字符
        content_html = content_html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        html += f'''
            <div class="message {msg_class}">
                <div class="message-header">
                    <span class="sender">{msg['sender']}</span>
                    <span class="time">{msg['time']}</span>
                </div>
                <div class="message-body">
                    {content_html}
                </div>
            </div>
'''

    html += f'''
        </div>

        <div class="footer">
            导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 使用 wechat-cli 生成
        </div>
    </div>

    <script>
        // 滚动到底部(显示最新消息)
        document.querySelector('.chat-container').scrollTop = document.querySelector('.chat-container').scrollHeight;
    </script>
</body>
</html>'''

    return html


def _generate_markdown(display_name, is_group, start_time, end_time, messages):
    """生成 Markdown 格式的聊天记录（对 AI 读取友好）"""

    chat_type = "群聊" if is_group else "私聊"
    msg_count = len(messages)

    md = f"# {display_name}\n\n"
    md += f"**类型**: {chat_type}  \n"
    md += f"**时间范围**: {start_time} 至 {end_time}  \n"
    md += f"**消息数**: {msg_count}\n\n"
    md += "---\n\n"

    for msg in messages:
        time_str = msg['time']
        sender = msg['sender']
        content = msg['content']

        # 发送者标记
        if msg['is_self']:
            sender_mark = "**我**"
        else:
            sender_mark = f"**{sender}**"

        # 格式化消息
        md += f"### {time_str}\n\n"
        md += f"{sender_mark}: {content}\n\n"

    md += "---\n\n"
    md += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    return md