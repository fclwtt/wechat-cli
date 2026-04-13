"""export-all-html 命令 - 导出所有聊天记录为 HTML"""

import click
import os
from pathlib import Path
from contextlib import closing
import sqlite3

from ..core.contacts import get_contact_names
from ..core.messages import resolve_chat_context
from .export_html import _collect_message_details, _generate_html, _generate_markdown


@click.command("export-all-html")
@click.option("--output", "output_path", default=None, help="输出目录路径")
@click.option("--limit", default=2000, help="每个聊天导出的消息数量")
@click.option("--copy-media", is_flag=True, help="复制图片/文件到输出目录")
@click.option("--max-chats", default=100, help="最多导出多少个聊天")
@click.pass_context
def export_all_html(ctx, output_path, limit, copy_media, max_chats):
    """导出所有聊天记录为 HTML 页面

    \b
    示例:
      wechat-cli export-all-html                     # 导出所有聊天到当前目录
      wechat-cli export-all-html --output ~/backup   # 导出到指定目录
      wechat-cli export-all-html --copy-media        # 同时复制媒体文件
    """
    app = ctx.obj

    # 确定输出目录
    if output_path:
        output_dir = Path(output_path)
    else:
        output_dir = Path.home() / "wechat-chats-backup"

    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"输出目录: {output_dir}")
    click.echo("")

    # 获取所有会话
    session_db = app.cache.get(os.path.join("session", "session.db"))
    if not session_db:
        click.echo("错误: 无法解密 session.db", err=True)
        ctx.exit(3)

    names = get_contact_names(app.cache, app.decrypted_dir)

    with closing(sqlite3.connect(session_db)) as conn:
        rows = conn.execute("""
            SELECT username, last_timestamp
            FROM SessionTable
            WHERE last_timestamp > 0
            ORDER BY last_timestamp DESC
            LIMIT ?
        """, (max_chats,)).fetchall()

    total = len(rows)
    click.echo(f"[1/2] 找到 {total} 个会话")
    click.echo("")

    if total == 0:
        click.echo("没有找到任何会话")
        ctx.exit(0)

    exported = 0
    failed = 0

    click.echo("[2/2] 开始导出...")
    click.echo("")

    for i, (username, ts) in enumerate(rows, 1):
        display_name = names.get(username, username)

        # 清理显示名称(用于文件名)
        safe_name = display_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        chat_dir = output_dir / safe_name

        click.echo(f"  [{i}/{total}] {display_name}")

        try:
            # 解析聊天上下文
            chat_ctx = resolve_chat_context(username, app.msg_db_keys, app.cache, app.decrypted_dir)
            if not chat_ctx or not chat_ctx.get('db_path'):
                click.echo(f"    跳过: 找不到聊天记录")
                continue

            # 创建聊天目录
            chat_dir.mkdir(parents=True, exist_ok=True)

            # 媒体目录
            media_dir = None
            if copy_media:
                media_dir = chat_dir / "media"
                media_dir.mkdir(exist_ok=True)

            # 收集消息详情
            messages = _collect_message_details(
                chat_ctx, names, app.display_name_fn,
                start_ts=None, end_ts=None, limit=limit,
                db_dir=app.db_dir, copy_media=copy_media, media_dir=media_dir
            )

            if not messages:
                click.echo(f"    跳过: 无消息")
                continue

            # 生成 HTML
            html_content = _generate_html(
                chat_ctx['display_name'],
                chat_ctx['is_group'],
                "最早", "最新",
                messages,
                copy_media
            )

            # 写入 HTML 文件
            html_path = chat_dir / "index.html"
            html_path.write_text(html_content, encoding="utf-8")

            # 生成 Markdown
            md_content = _generate_markdown(
                chat_ctx['display_name'],
                chat_ctx['is_group'],
                "最早", "最新",
                messages,
                copy_media
            )

            # 写入 Markdown 文件
            md_path = chat_dir / "index.md"
            md_path.write_text(md_content, encoding="utf-8")

            exported += 1

        except Exception as e:
            click.echo(f"    失败: {e}")
            failed += 1

    click.echo("")
    click.echo("=" * 60)
    click.echo("导出完成")
    click.echo("=" * 60)
    click.echo(f"成功: {exported} 个聊天")
    click.echo(f"失败: {failed} 个聊天")
    click.echo(f"输出: {output_dir}")
    click.echo("")
    click.echo("使用方法:")
    click.echo(f"  1. 打开文件夹: {output_dir}")
    click.echo("  2. 进入任意聊天目录")
    click.echo("  3. 双击 index.html 查看")