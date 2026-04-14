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
            'time': time_str.replace('[', '').replace(']', ''),
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
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
            background: #ededed;
            min-height: 100vh;
        }}

        .chat-window {{
            max-width: 800px;
            margin: 0 auto;
            background: #ededed;
            min-height: 100vh;
        }}

        /* 顶部标题栏 */
        .header {{
            background: #ededed;
            padding: 12px 20px;
            border-bottom: 1px solid #d9d9d9;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .header-content {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .avatar-header {{
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #07c160 0%, #06ad56 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
        }}

        .header-info {{
            flex: 1;
        }}

        .header h1 {{
            font-size: 17px;
            font-weight: 500;
            color: #000;
        }}

        .header .meta {{
            font-size: 12px;
            color: #888;
        }}

        /* 背景区域 */
        .bg-area {{
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23ededed" width="100" height="100"/><circle cx="25" cy="25" r="20" fill="%23e0e0e0" opacity="0.3"/><circle cx="75" cy="75" r="30" fill="%23e0e0e0" opacity="0.2"/></svg>') repeat;
            background-size: 200px;
            background-color: #ededed;
            padding-bottom: 60px;
            min-height: calc(100vh - 120px);
        }}

        /* 消息区域 */
        .chat-container {{
            padding: 16px;
            max-width: 800px;
            margin: 0 auto;
        }}

        .message {{
            margin-bottom: 16px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }}

        .message.self {{
            flex-direction: row-reverse;
        }}

        /* 头像 */
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 4px;
            background: #ccc;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            color: white;
            flex-shrink: 0;
        }}

        .avatar.self {{
            background: linear-gradient(135deg, #07c160 0%, #06ad56 100%);
        }}

        .avatar.other {{
            background: linear-gradient(135deg, #576b95 0%, #4a5c80 100%);
        }}

        /* 消息内容 */
        .msg-content {{
            max-width: 70%;
            position: relative;
        }}

        .sender-name {{
            font-size: 12px;
            color: #888;
            margin-bottom: 4px;
            padding-left: 12px;
        }}

        .message.self .sender-name {{
            display: none;
        }}

        .bubble {{
            padding: 10px 14px;
            border-radius: 8px;
            word-wrap: break-word;
            white-space: pre-wrap;
            font-size: 15px;
            line-height: 1.5;
            position: relative;
        }}

        .message.self .bubble {{
            background: #95ec69;
            color: #000;
        }}

        .message.other .bubble {{
            background: #fff;
            color: #000;
        }}

        /* 时间 */
        .time-separator {{
            text-align: center;
            padding: 12px 0;
            font-size: 12px;
            color: #b2b2b2;
        }}

        /* 底部统计 */
        .footer {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #f7f7f7;
            border-top: 1px solid #d9d9d9;
            padding: 12px;
            text-align: center;
            font-size: 12px;
            color: #888;
            max-width: 800px;
            margin: 0 auto;
        }}

        .footer-content {{
            display: flex;
            justify-content: center;
            gap: 20px;
        }}

        .stat {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .stat-num {{
            font-weight: 600;
            color: #07c160;
        }}

        /* 响应式 */
        @media (max-width: 600px) {{
            .bubble {{
                max-width: 85%;
            }}
            .msg-content {{
                max-width: 85%;
            }}
        }}
    </style>
</head>
<body>
    <div class="chat-window">
        <div class="header">
            <div class="header-content">
                <div class="avatar-header">{"👥" if is_group else "👤"}</div>
                <div class="header-info">
                    <h1>{display_name}</h1>
                    <div class="meta">{chat_type} · {msg_count}条消息</div>
                </div>
            </div>
        </div>

        <div class="bg-area">
            <div class="chat-container">
'''

    # 添加消息
    for msg in messages:
        msg_class = "self" if msg['is_self'] else "other"
        content_html = msg['content']

        # 转义 HTML 特殊字符
        content_html = content_html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 头像图标
        avatar_icon = "💬" if msg['is_self'] else "👤"

        html += f'''                <div class="message {msg_class}">
                    <div class="avatar {msg_class}">{avatar_icon}</div>
                    <div class="msg-content">
                        <div class="sender-name">{msg['sender']}</div>
                        <div class="bubble">{content_html}</div>
                    </div>
                </div>
'''

    html += f'''            </div>
        </div>

        <div class="footer">
            <div class="footer-content">
                <div class="stat">
                    <span>时间范围:</span>
                    <span>{start_time} ~ {end_time}</span>
                </div>
                <div class="stat">
                    <span>导出时间:</span>
                    <span>{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
                </div>
            </div>
        </div>
    </div>

'''

    return html

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