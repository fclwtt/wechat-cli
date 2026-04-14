"""export-html 命令 - 导出聊天记录为美观的 HTML 页面"""

import click
import os
import base64
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
@click.option("--copy-media", is_flag=True, help="复制图片/文件到输出目录")
@click.pass_context
def export_html(ctx, chat_name, output_path, start_time, end_time, limit, copy_media):
    """导出聊天记录为美观的 HTML 页面

    \b
    示例:
      wechat-cli export-html "张三"
      wechat-cli export-html "工作群" --output D:\\backup\\chats
      wechat-cli export-html "张三" --start-time "2026-04-01" --copy-media
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

    # 创建目录结构
    safe_name = chat_ctx['display_name'].replace('/', '_').replace('\\', '_').replace(':', '_')
    html_dir = out_dir / safe_name
    media_dir = html_dir / "media"
    html_dir.mkdir(parents=True, exist_ok=True)
    if copy_media:
        media_dir.mkdir(exist_ok=True)

    # 收集消息详情(包含时间、发送者、内容、类型等)
    messages = _collect_message_details(
        chat_ctx, names, app.display_name_fn,
        start_ts=start_ts, end_ts=end_ts, limit=limit,
        db_dir=app.db_dir, copy_media=copy_media, media_dir=media_dir
    )

    # 生成 HTML
    html_content = _generate_html(
        chat_ctx['display_name'],
        chat_ctx['is_group'],
        start_time or "最早",
        end_time or "最新",
        messages,
        copy_media
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
        copy_media
    )

    # 写入 Markdown 文件
    md_file = html_dir / "index.md"
    md_file.write_text(md_content, encoding='utf-8')

    click.echo(f"已导出: {html_file}", err=True)
    click.echo(f"Markdown: {md_file}", err=True)
    click.echo(f"消息数: {len(messages)}", err=True)
    if copy_media:
        click.echo(f"媒体目录: {media_dir}", err=True)


def _collect_message_details(chat_ctx, names, display_name_fn, start_ts, end_ts, limit, db_dir=None, copy_media=False, media_dir=None):
    """收集消息详情,包含媒体处理"""
    from ..core.messages import _iter_table_contexts, _query_messages, _format_message_text
    import hashlib

    # 调试输出
    debug = True  # 临时启用调试

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

            # 解压内容
            if wcdb_content:
                try:
                    from ..core.messages import _decompress_content
                    content = _decompress_content(wcdb_content)
                except:
                    pass

            # 解析消息
            base_type = local_type & 0xFFFFFFFF
            sub_type = (local_type >> 32) & 0xFFFFFFFF

            # 获取发送者
            sender_name = display_name_fn(real_sender_id, names) if real_sender_id else "我"

            # 格式化时间
            msg_time = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')

            # 解析内容
            msg_content = _parse_content(content, base_type, sub_type)

            # 简化：图片和视频显示占位符，不复制媒体
            media_path = None
            media_type = None
            media_copied = False
            
            # 文件（type=49）保留处理
            if base_type == 49:
                # 调试：看看 XML 内容
                if debug:
                    print(f"    [DEBUG] type=49 content[:500]: {content[:500] if content else 'None'}")
                original_path = _resolve_media_path(db_dir, content, base_type, create_time, ctx.get('username'), debug=debug)
                if original_path and isinstance(original_path, str) and os.path.exists(original_path):
                    media_type = 'file'
                    if copy_media and media_dir:
                        ext = Path(original_path).suffix
                        safe_filename = f"{create_time}_{local_id}{ext}"
                        copied_path = media_dir / safe_filename
                        try:
                            import shutil
                            shutil.copy2(original_path, copied_path)
                            media_path = f"media/{safe_filename}"
                            media_copied = True
                            if debug:
                                print(f"    [DEBUG] 文件复制成功: {copied_path}")
                        except:
                            pass

            messages.append({
                'time': msg_time,
                'sender': sender_name,
                'content': msg_content,
                'type': base_type,
                'media_path': media_path,
                'media_type': media_type,
                'media_copied': media_copied,
                'is_self': not real_sender_id,
            })

            total += 1
            if total >= limit:
                break

        conn.close()

        if total >= limit:
            break

    return messages


def _parse_content(content, base_type, sub_type):
    """解析消息内容"""
    if not content:
        return ""

    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8', errors='replace')
        except:
            content = str(content)

    # 文本消息
    if base_type == 1:
        return content.strip()

    # 图片
    if base_type == 3:
        return "[图片]"

    # 视频
    if base_type == 43:
        return "[视频]"

    # 文件
    if base_type == 49:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content[:20000])
            appmsg = root.find('.//appmsg')
            if appmsg:
                app_type = int((appmsg.findtext('type') or '0').strip())
                title = (appmsg.findtext('title') or '').strip()

                # 根据子类型区分
                if app_type == 6:
                    return f"[文件] {title}" if title else "[文件]"
                elif app_type == 33 or app_type == 36:
                    return f"[小程序] {title}" if title else "[小程序]"
                elif app_type == 4:
                    return f"[视频] {title}" if title else "[视频]"
                elif app_type == 5:
                    url = (appmsg.findtext('url') or '').strip()
                    return f"[链接] {title}\n{url}" if title else "[链接]"
                elif app_type == 1 or app_type == 0:
                    # 文本分享,直接显示内容
                    return title if title else "[分享]"
                else:
                    return f"[分享] {title}" if title else "[分享]"
            return "[分享]"
        except:
            return "[分享]"

    # 语音
    if base_type == 34:
        return "[语音]"

    # 表情
    if base_type == 47:
        return "[表情]"

    # 系统
    if base_type == 10000:
        return content.strip()

    return f"[消息] {content[:100]}"


def _resolve_media_path(db_dir, content, base_type, create_time, chat_username=None, debug=False):
    """解析媒体文件路径,返回具体文件路径"""
    from datetime import datetime
    import hashlib
    import xml.etree.ElementTree as ET
    import glob

    if debug:
        print(f"    [DEBUG] _resolve_media_path: db_dir={db_dir}, base_type={base_type}, create_time={create_time}, username={chat_username}")

    if not db_dir:
        if debug:
            print("    [DEBUG] db_dir is None, return None")
        return None

    wechat_base = Path(db_dir).parent
    msg_dir = wechat_base / "msg"

    if debug:
        print(f"    [DEBUG] wechat_base={wechat_base}, msg_dir={msg_dir}, exists={msg_dir.exists()}")

    if not msg_dir.exists():
        if debug:
            print("    [DEBUG] msg_dir not exists")
        return None

    dt = datetime.fromtimestamp(create_time)
    date_prefix = dt.strftime("%Y-%m")
    date_prefix2 = dt.strftime("%Y%m")  # 有些目录用这种格式

    # 文件
    if base_type == 49 and content:
        try:
            root = ET.fromstring(content[:20000])
            appmsg = root.find('.//appmsg')
            if appmsg:
                app_type = int((appmsg.findtext('type') or '0').strip())
                if app_type == 6:
                    title = (appmsg.findtext('title') or '').strip()
                    if title:
                        file_dir = msg_dir / "file" / date_prefix
                        if file_dir.exists():
                            target = file_dir / title
                            if target.exists():
                                return str(target)
                            # 模糊匹配
                            for f in file_dir.iterdir():
                                if title in f.name or f.name in title:
                                    return str(f)
        except:
            pass

    # 图片 - 微信 4.x 加密格式,暂不支持解码
    if base_type == 3:
        if debug:
            print("    [DEBUG] 图片: 微信4.x加密格式,暂不支持解码")
        return None  # 暂时返回 None,显示占位符

    # 视频 - 需要匹配具体文件
    if base_type == 43:
        video_dir = msg_dir / "video" / date_prefix
        if debug:
            print(f"    [DEBUG] 视频: video_dir={video_dir}, exists={video_dir.exists()}")
        if video_dir.exists():
            # 用时间戳匹配具体文件
            result = _find_video_by_time(video_dir, create_time, debug=debug)
            if debug:
                print(f"    [DEBUG] 视频: _find_video_by_time 返回 {result}")
            return result

        # 尝试其他格式
        video_dir2 = msg_dir / "video" / date_prefix2
        if debug:
            print(f"    [DEBUG] 视频: video_dir2={video_dir2}, exists={video_dir2.exists()}")
        if video_dir2.exists():
            return _find_video_by_time(video_dir2, create_time, debug=debug)

    return None


def _find_image_by_time(img_dir, create_time):
    """根据时间戳查找图片文件"""
    # 查找所有 .dat 文件(微信加密图片)
    dat_files = list(img_dir.glob("*.dat"))
    if not dat_files:
        # 也查找 .jpg, .png 等
        dat_files = list(img_dir.glob("*.*"))

    if not dat_files:
        return None

    # 找时间最近的文件
    dt = datetime.fromtimestamp(create_time)
    target_time = dt.timestamp()

    best_file = None
    best_diff = float('inf')

    for f in dat_files:
        try:
            # 文件名可能包含时间戳信息
            # 或者用文件修改时间匹配
            file_mtime = f.stat().st_mtime
            diff = abs(file_mtime - target_time)
            if diff < best_diff:
                best_diff = diff
                best_file = f
        except:
            pass

    # 如果时间差在 60 秒内,返回该文件
    if best_file and best_diff < 60:
        return str(best_file)

    # 否则返回第一个文件(如果只有一个)
    if len(dat_files) == 1:
        return str(dat_files[0])

    return None


def _find_video_by_time(video_dir, create_time, debug=False):
    """根据时间戳查找视频文件和缩略图"""
    # 查找所有视频文件
    video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.avi"))

    if debug:
        print(f"      [DEBUG] _find_video_by_time: 找到 {len(video_files)} 个视频文件")
        if video_files:
            print(f"      [DEBUG] 视频文件: {[f.name for f in video_files[:5]]}")

    if not video_files:
        return None

    # 找时间最近的文件
    dt = datetime.fromtimestamp(create_time)
    target_time = dt.timestamp()

    if debug:
        print(f"      [DEBUG] 消息时间: {dt.strftime('%Y-%m-%d %H:%M:%S')} ({target_time})")

    best_file = None
    best_thumb = None
    best_diff = float('inf')

    for f in video_files:
        try:
            file_mtime = f.stat().st_mtime
            diff = abs(file_mtime - target_time)
            if debug:
                print(f"      [DEBUG] {f.name}: mtime={datetime.fromtimestamp(file_mtime).strftime('%H:%M:%S')}, diff={diff:.0f}s")
            if diff < best_diff:
                best_diff = diff
                best_file = f
                # 查找对应的缩略图
                thumb_name = f.stem + "_thumb.jpg"
                thumb_path = video_dir / thumb_name
                best_thumb = thumb_path if thumb_path.exists() else None
        except Exception as e:
            if debug:
                print(f"      [DEBUG] {f.name}: error={e}")

    if debug:
        print(f"      [DEBUG] best_file={best_file.name if best_file else None}, best_diff={best_diff:.0f}s")

    # 放宽匹配条件(视频文件可能很多,无法精确匹配):
    # 1. 时间差 < 60s:精确匹配
    # 2. 时间差 < 600s(10分钟):模糊匹配
    # 3. 视频文件 <= 10个:返回时间最接近的
    # 4. 文件 > 10个:只要找到最近的就返回(标注为不确定匹配)
    if best_file:
        if best_diff < 60:
            result = {'video': str(best_file), 'thumb': str(best_thumb) if best_thumb else None}
            if debug:
                print(f"      [DEBUG] 精确匹配 (<60s): {best_file.name}")
            return result
        elif best_diff < 600 or len(video_files) <= 10:
            result = {'video': str(best_file), 'thumb': str(best_thumb) if best_thumb else None}
            if debug:
                print(f"      [DEBUG] 模糊匹配 (diff={best_diff:.0f}s, files={len(video_files)}): {best_file.name}")
            return result
        else:
            # 即使时间差很大,也返回最近的文件(但标注为不确定)
            result = {'video': str(best_file), 'thumb': str(best_thumb) if best_thumb else None}
            if debug:
                print(f"      [DEBUG] 不确定匹配 (diff={best_diff:.0f}s, files={len(video_files)}): {best_file.name}")
            return result

    return None


def _generate_html(display_name, is_group, start_time, end_time, messages, copy_media):
    """生成美观的 HTML 页面"""

    chat_type = "群聊" if is_group else "私聊"

    # 消息数量统计
    msg_count = len(messages)
    image_count = sum(1 for m in messages if m['type'] == 3)
    file_count = sum(1 for m in messages if m['type'] == 49)

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
            justify-content: center;
            gap: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}

        .stat-item {{
            text-align: center;
        }}

        .stat-item .number {{
            font-size: 24px;
            font-weight: 600;
            color: #667eea;
        }}

        .stat-item .label {{
            font-size: 12px;
            color: #6c757d;
        }}

        .chat-container {{
            padding: 20px;
            max-height: 70vh;
            overflow-y: auto;
        }}

        .message {{
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
        }}

        .message.self {{
            align-items: flex-end;
        }}

        .message.other {{
            align-items: flex-start;
        }}

        .message-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
            font-size: 12px;
        }}

        .message.self .message-header {{
            flex-direction: row-reverse;
        }}

        .sender {{
            font-weight: 600;
            color: #495057;
        }}

        .time {{
            color: #adb5bd;
        }}

        .message-body {{
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 12px;
            font-size: 15px;
            line-height: 1.5;
        }}

        .message.self .message-body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .message.other .message-body {{
            background: #f1f3f4;
            color: #202124;
        }}

        .message.system .message-body {{
            background: #fff3cd;
            color: #856404;
            max-width: 100%;
            text-align: center;
            font-size: 13px;
        }}

        .media-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: rgba(255,255,255,0.2);
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
            text-decoration: none;
            color: inherit;
        }}

        .media-link:hover {{
            background: rgba(255,255,255,0.3);
        }}

        .media-icon {{
            font-size: 18px;
        }}

        .file-info {{
            font-size: 13px;
            opacity: 0.8;
        }}

        .footer {{
            padding: 20px;
            background: #f8f9fa;
            text-align: center;
            font-size: 12px;
            color: #6c757d;
        }}

        /* 滚动条样式 */
        .chat-container::-webkit-scrollbar {{
            width: 8px;
        }}

        .chat-container::-webkit-scrollbar-track {{
            background: #f1f1f1;
        }}

        .chat-container::-webkit-scrollbar-thumb {{
            background: #c1c1c1;
            border-radius: 4px;
        }}

        .chat-container::-webkit-scrollbar-thumb:hover {{
            background: #a8a8a8;
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
            <div class="stat-item">
                <div class="number">{image_count}</div>
                <div class="label">图片</div>
            </div>
            <div class="stat-item">
                <div class="number">{file_count}</div>
                <div class="label">文件</div>
            </div>
        </div>

        <div class="chat-container">
'''

    # 添加消息
    for msg in messages:
        msg_class = "self" if msg['is_self'] else ("system" if msg['type'] == 10000 else "other")

        # 内容处理
        content_html = msg['content']

        # 媒体链接
        if msg.get('media_path') and msg.get('media_copied'):
            # 已复制的媒体文件
            if msg['media_type'] == 'image':
                # 图片直接嵌入显示
                content_html = f'<img src="{msg["media_path"]}" style="max-width: 300px; border-radius: 8px; cursor: pointer;" onclick="window.open(this.src)" title="点击查看大图">'
            elif msg['media_type'] == 'video':
                # 视频嵌入播放,支持缩略图
                thumb = msg.get('thumb_path')
                if thumb:
                    content_html = f'''<div style="position: relative; max-width: 300px;">
                            <video poster="{thumb}" style="max-width: 300px; border-radius: 8px;" controls>
                                <source src="{msg['media_path']}" type="video/mp4">
                            </video>
                        </div>'''
                else:
                    content_html = f'<video src="{msg["media_path"]}" style="max-width: 300px; border-radius: 8px;" controls></video>'
            elif msg['media_type'] == 'file':
                content_html = f'''
                    <a href="{msg['media_path']}" class="media-link" download>
                        <span class="media-icon">📎</span>
                        <span class="file-info">{msg['content']}</span>
                    </a>
                    '''
        elif msg.get('media_path'):
            # 原始路径(点击打开文件夹)
            original_path = msg['media_path'].replace('\\', '/')
            content_html = f'''
                <a href="file:///{original_path}" class="media-link" title="点击打开文件位置">
                    <span class="media-icon">📁</span>
                    <span class="file-info">{msg['content']}</span>
                </a>
                '''
        elif msg['type'] == 3:
            # 图片占位符
            content_html = '<div style="padding: 12px; background: #f0f0f0; border-radius: 8px; color: #888; font-size: 13px;">📷 [图片]</div>'
        elif msg['type'] == 43:
            # 视频占位符
            content_html = '<div style="padding: 12px; background: #f0f0f0; border-radius: 8px; color: #888; font-size: 13px;">🎬 [视频]</div>'

        # 转义 HTML 特殊字符(但保留我们生成的链接)
        if '<a' not in content_html and '<img' not in content_html and '<video' not in content_html:
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
            导出时间:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 使用 wechat-cli 生成
        </div>
    </div>

    <script>
        // 滚动到底部(显示最新消息)
        document.querySelector('.chat-container').scrollTop = document.querySelector('.chat-container').scrollHeight;

        // 文件链接点击事件(打开文件夹)
        document.querySelectorAll('a[href^="file:///"]').forEach(link => {{
            link.addEventListener('click', function(e) {{
                e.preventDefault();
                const path = this.getAttribute('href').replace('file:///', '');
                alert('文件路径: ' + path + '\\n\\n请在文件资源管理器中打开此路径');
            }});
        }});
    </script>
</body>
</html>'''

    return html


def _generate_markdown(display_name, is_group, start_time, end_time, messages, copy_media):
    """生成 Markdown 格式的聊天记录(对 AI 读取友好)"""

    chat_type = "群聊" if is_group else "私聊"
    msg_count = len(messages)

    md = f"# {display_name}\n\n"
    md += f"**类型**: {chat_type}  \n"
    md += f"**时间范围**: {start_time} 至 {end_time}  \n"
    md += f"**消息数**: {msg_count}\n\n"
    md += "---\n\n"

    for msg in messages:
        # 时间戳
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

        # 媒体处理
        if msg['type'] == 3:
            content = "📷 [图片]"
        elif msg['type'] == 43:
            content = "🎬 [视频]"
        elif msg['media_path'] and msg['media_copied']:
            if msg['media_type'] == 'file':
                content = f"📎 [文件: {msg['content']}]"

        # 格式化消息
        md += f"### {time_str}\n\n"
        md += f"{sender_mark}: {content}\n\n"

    md += "---\n\n"
    md += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    return md