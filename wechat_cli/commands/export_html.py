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

    # 收集消息详情
    messages = _collect_message_details(
        chat_ctx, names, app.display_name_fn,
        start_ts=start_ts, end_ts=end_ts, limit=limit,
        db_dir=app.db_dir
    )

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


def _collect_message_details(chat_ctx, names, display_name_fn, start_ts, end_ts, limit, db_dir=None):
    """收集消息详情（纯文字版）"""
    from ..core.messages import _iter_table_contexts, _query_messages

    messages = []
    total = 0

    for ctx in _iter_table_contexts(chat_ctx):
        if not ctx['db_path'] or not ctx['table_name']:
            continue

        import sqlite3
        conn = sqlite3.connect(ctx['db_path'])

        rows = _query_messages(
            conn, ctx['table_name'],
            start_ts=start_ts, end_ts=end_ts, keyword='', limit=limit, offset=total
        )

        for row in rows:
            local_id, local_type, create_time, real_sender_id, content, wcdb_content = row

            # 解析消息类型
            base_type = local_type & 0xFFFFFFFF

            # 解析内容（纯文字）
            msg_content = _parse_content_simple(content, base_type)

            # 获取发送者
            sender_name = display_name_fn(real_sender_id, names) if real_sender_id else "我"

            # 格式化时间
            msg_time = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')

            messages.append({
                'time': msg_time,
                'sender': sender_name,
                'content': msg_content,
                'type': base_type,
                'is_self': not real_sender_id,
            })

            total += 1
            if total >= limit:
                break

        conn.close()

        if total >= limit:
            break

    return messages


def _parse_content_simple(content, base_type):
    """简化版内容解析（纯文字）"""
    if not content:
        return ""

    # 处理 bytes 类型
    if isinstance(content, bytes):
        # 尝试 zlib 解压
        try:
            import zlib
            decompressed = zlib.decompress(content, wbits=-15)
            content = decompressed.decode('utf-8', errors='replace')
        except:
            try:
                import zlib
                decompressed = zlib.decompress(content[4:], wbits=-15)
                content = decompressed.decode('utf-8', errors='replace')
            except:
                # 解压失败，显示占位符
                return _get_placeholder(base_type)

    # 文本消息
    if base_type == 1:
        return content.strip() if isinstance(content, str) else ""

    # 图片
    if base_type == 3:
        return "📷 [图片]"

    # 视频
    if base_type == 43:
        return "🎬 [视频]"

    # 文件/链接/小程序（type=49，无法解析压缩内容）
    if base_type == 49:
        return "📎 [分享]"

    # 语音
    if base_type == 34:
        return "🎤 [语音]"

    # 表情
    if base_type == 47:
        return "😀 [表情]"

    # 系统
    if base_type == 10000:
        return content.strip() if isinstance(content, str) else ""

    return f"[消息]"


def _get_placeholder(base_type):
    """获取媒体占位符"""
    placeholders = {
        1: "[文本]",
        3: "📷 [图片]",
        34: "🎤 [语音]",
        43: "🎬 [视频]",
        47: "😀 [表情]",
        49: "📎 [分享]",
        10000: "[系统消息]",
    }
    return placeholders.get(base_type, "[消息]")


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
        msg_class = "self" if msg['is_self'] else ("system" if msg['type'] == 10000 else "other")
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
        elif msg['type'] == 10000:
            sender_mark = "*系统*"
        else:
            sender_mark = f"**{sender}**"

        # 格式化消息
        md += f"### {time_str}\n\n"
        md += f"{sender_mark}: {content}\n\n"

    md += "---\n\n"
    md += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    return md