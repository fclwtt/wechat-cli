"""export-html 命令 - 导出聊天记录为美观的 HTML 页面（纯文字版）"""

import click
import os
from datetime import datetime
from pathlib import Path

from ..core.contacts import get_contact_names, get_self_username
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
    
    names = get_contact_names(app.cache, app.decrypted_dir)

    # 获取账号自己的 username
    self_username = get_self_username(app.db_dir, app.cache, app.decrypted_dir)

    # 添加 self_username 到 chat_ctx
    chat_ctx['self_username'] = self_username
    
    if not chat_ctx['db_path']:
        click.echo(f"找不到 {chat_ctx['display_name']} 的消息记录", err=True)
        ctx.exit(1)

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
    is_group_chat = chat_ctx.get('is_group', False)
    for line in lines:
        # line 格式: "[时间] 发送者: 内容" 或 "[时间] 内容"
        # 私聊中：自己发送的消息没有发送者前缀
        # 群聊中：所有消息都有发送者前缀
        
        # 先去掉时间前缀 [YYYY-MM-DD HH:MM]
        line_content = line
        if line.startswith('[') and '] ' in line:
            time_str = line.split('] ', 1)[0].replace('[', '')
            line_content = line.split('] ', 1)[1]
        else:
            time_str = ''
            line_content = line
        
        # 判断发送者和是否是自己
        if ': ' in line_content:
            sender_part, content = line_content.split(': ', 1)
            # 自己的消息：发送者是 self_username 或 '我'
            is_self = sender_part == self_username or sender_part == '我'
        else:
            # 没有发送者前缀（理论上不会再出现，因为 _resolve_sender_label 已修复）
            sender_part = ''
            content = line_content
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
            background: linear-gradient(135deg, #0c0c1e 0%, #1a1a3e 30%, #2d2d5e 60%, #0f0f2e 100%);
            min-height: 100vh;
            position: relative;
        }}

        /* 全屏科技感网格背景 */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: 
                linear-gradient(rgba(100,150,255,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(100,150,255,0.03) 1px, transparent 1px);
            background-size: 40px 40px;
            z-index: -1;
        }}

        /* 光晕效果 */
        body::after {{
            content: '';
            position: fixed;
            top: 30%;
            left: 20%;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(102,126,234,0.08) 0%, transparent 70%);
            z-index: -1;
            animation: glow1 8s ease-in-out infinite alternate;
        }}

        /* 第二个光晕 */
        .glow2 {{
            position: fixed;
            bottom: 20%;
            right: 10%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(118,75,162,0.08) 0%, transparent 70%);
            z-index: -1;
            animation: glow2 6s ease-in-out infinite alternate;
        }}

        @keyframes glow1 {{
            0% {{ transform: translate(0, 0); opacity: 0.5; }}
            100% {{ transform: translate(50px, 30px); opacity: 0.8; }}
        }}

        @keyframes glow2 {{
            0% {{ transform: translate(0, 0); opacity: 0.5; }}
            100% {{ transform: translate(-30px, 50px); opacity: 0.8; }}
        }}

        .chat-window {{
            max-width: 800px;
            margin: 0 auto;
            background: #ededed;
            min-height: 100vh;
        }}

        /* 顶部标题栏 */
        .header {{
            background: rgba(26,26,46,0.95);
            padding: 12px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
            box-shadow: 0 2px 8px rgba(102,126,234,0.4);
        }}

        .header-info {{
            flex: 1;
        }}

        .header h1 {{
            font-size: 17px;
            font-weight: 500;
            color: #fff;
        }}

        .header .meta {{
            font-size: 12px;
            color: rgba(255,255,255,0.7);
        }}

        /* 背景区域 */
        .bg-area {{
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 8px rgba(102,126,234,0.4);
        }}

        .avatar.other {{
            background: rgba(255,255,255,0.9);
            color: #1a1a2e;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}

        /* 消息内容 */
        .msg-content {{
            max-width: 70%;
            position: relative;
        }}

        .msg-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
            padding-left: 12px;
        }}

        .sender-name {{
            font-size: 12px;
            color: rgba(255,255,255,0.9);
        }}

        .msg-time {{
            font-size: 11px;
            color: rgba(255,255,255,0.6);
        }}

        /* 对方消息的昵称+时间：深色文字 */
        .message.other .msg-meta {{
            color: rgba(0,0,0,0.8);
        }}

        .message.other .sender-name {{
            color: rgba(0,0,0,0.9);
        }}

        .message.other .msg-time {{
            color: rgba(0,0,0,0.6);
        }}

        /* 自己消息的昵称+时间：右对齐 */
        .message.self .msg-meta {{
            justify-content: flex-end;
            padding-left: 0;
            padding-right: 12px;
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            box-shadow: 0 2px 8px rgba(102,126,234,0.3);
        }}

        .message.other .bubble {{
            background: rgba(255,255,255,0.9);
            color: #1a1a2e;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
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
            background: rgba(26,26,46,0.95);
            border-top: 1px solid rgba(255,255,255,0.1);
            padding: 12px;
            text-align: center;
            font-size: 12px;
            color: rgba(255,255,255,0.7);
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
    <div class="glow2"></div>
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
                        <div class="msg-meta">
                            <div class="sender-name">{msg['sender']}</div>
                            <div class="msg-time">{msg['time']}</div>
                        </div>
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