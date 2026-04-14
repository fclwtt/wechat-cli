"""export-all-accounts 命令 - 导出所有账号的聊天记录"""

import click
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from ..core.config import ACCOUNTS_DIR, ACCOUNTS_INDEX_FILE, list_accounts, load_account_config
from ..core.db_cache import DBCache
from ..core.contacts import get_contact_names
from ..core.messages import resolve_chat_context


@click.command("export-all-accounts")
@click.option("--output", "output_path", default=None, help="输出目录路径")
@click.option("--limit", default=2000, help="每个聊天导出的消息数量")
@click.option("--max-chats", default=100, help="每个账号最多导出多少个聊天")
@click.option("--start-time", default=None, help="开始时间 (YYYY-MM-DD)")
@click.option("--end-time", default=None, help="结束时间 (YYYY-MM-DD)")
@click.option("--debug", is_flag=True, help="显示详细调试信息")
def export_all_accounts(output_path, limit, max_chats, start_time, end_time, debug):
    """导出所有账号的聊天记录为 HTML 页面

    \b
    示例:
      wechat-cli export-all-accounts                     # 导出到 ~/wechat-chats-backup/
      wechat-cli export-all-accounts --output ~/backup   # 导出到指定目录
      wechat-cli export-all-accounts --copy-media        # 同时复制媒体文件
      wechat-cli export-all-accounts --start-time 2026-04-12 --end-time 2026-04-12  # 每日导出
      wechat-cli export-all-accounts --debug             # 显示调试信息
    """
    # 调试输出函数
    def debug_log(msg):
        if debug:
            click.echo(f"[DEBUG] {msg}")

    debug_log(f"ACCOUNTS_DIR = {ACCOUNTS_DIR}")
    debug_log(f"ACCOUNTS_INDEX_FILE = {ACCOUNTS_INDEX_FILE}")
    debug_log(f"accounts index exists = {os.path.exists(ACCOUNTS_INDEX_FILE)}")

    # 获取所有账号
    accounts = list_accounts()
    debug_log(f"Found accounts: {accounts}")

    if not accounts:
        click.echo("错误: 未找到任何账号,请先运行 wechat-cli init --all", err=True)
        click.echo("")
        click.echo("调试信息:")
        click.echo(f"  账号目录: {ACCOUNTS_DIR}")
        click.echo(f"  目录存在: {os.path.exists(ACCOUNTS_DIR)}")
        if os.path.exists(ACCOUNTS_DIR):
            subdirs = [d for d in os.listdir(ACCOUNTS_DIR) if os.path.isdir(os.path.join(ACCOUNTS_DIR, d))]
            click.echo(f"  子目录: {subdirs}")
        click.echo(f"  索引文件: {ACCOUNTS_INDEX_FILE}")
        click.echo(f"  索引存在: {os.path.exists(ACCOUNTS_INDEX_FILE)}")
        exit(1)

    # 解析时间范围
    start_ts, end_ts = None, None
    if start_time or end_time:
        from datetime import datetime
        if start_time:
            start_ts = int(datetime.strptime(start_time, "%Y-%m-%d").timestamp())
        if end_time:
            # 结束时间设为当天 23:59:59
            end_dt = datetime.strptime(end_time, "%Y-%m-%d")
            end_ts = int(end_dt.replace(hour=23, minute=59, second=59).timestamp())

    # 确定输出目录
    if output_path:
        output_dir = Path(output_path)
    else:
        output_dir = Path.home() / "wechat-chats-backup"

    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo("=" * 60)
    click.echo("  导出所有账号聊天记录")
    click.echo("=" * 60)
    click.echo(f"账号数: {len(accounts)}")
    click.echo(f"输出目录: {output_dir}")
    if start_ts or end_ts:
        click.echo(f"时间范围: {start_time or '最早'} 至 {end_time or '最新'}")
    click.echo("")

    for wxid in accounts:
        click.echo(f"\n[账号] {wxid}")
        click.echo("-" * 40)

        try:
            _export_account(wxid, output_dir, limit, max_chats, start_ts, end_ts, start_time, end_time, debug)
        except Exception as e:
            click.echo(f"  导出失败: {e}", err=True)

    click.echo("")
    click.echo("=" * 60)
    click.echo("全部导出完成")
    click.echo("=" * 60)
    click.echo(f"输出: {output_dir}")
    click.echo("")
    click.echo("使用方法:")
    click.echo(f"  1. 打开文件夹: {output_dir}")
    click.echo("  2. 进入账号目录 → 聊天目录 → 双击 index.html")


def _export_account(wxid, output_dir, limit, max_chats, start_ts=None, end_ts=None, start_time=None, end_time=None, debug=False):
    """导出单个账号的所有聊天"""
    import json
    from .export_html import _collect_message_details, _generate_html, _generate_markdown

    # 调试输出函数
    def debug_log(msg):
        if debug:
            click.echo(f"    [DEBUG] {msg}")

    # 加载配置
    cfg = load_account_config(wxid)
    db_dir = cfg["db_dir"]
    keys_file = cfg["keys_file"]
    decrypted_dir = cfg.get("decrypted_dir", os.path.join(ACCOUNTS_DIR, wxid, "decrypted"))

    debug_log(f"db_dir = {db_dir}")
    debug_log(f"keys_file = {keys_file}")
    debug_log(f"keys_file exists = {os.path.exists(keys_file)}")

    # 加载密钥
    keys_json = json.load(open(keys_file))
    from ..core.key_utils import strip_key_metadata
    all_keys = strip_key_metadata(keys_json)

    debug_log(f"all_keys count = {len(all_keys)}")

    # 初始化 cache
    cache = DBCache(all_keys, db_dir)
    debug_log(f"cache initialized")

    # 获取 msg_db_keys
    msg_db_keys = [k for k in keys_json.keys() if k.startswith("message/") or k.startswith("message\\")]
    debug_log(f"msg_db_keys count = {len(msg_db_keys)}")
    if msg_db_keys:
        debug_log(f"msg_db_keys sample: {msg_db_keys[:3]}...")

    # 获取联系人
    names = get_contact_names(cache, decrypted_dir)

    # 显示名称函数
    def display_name_fn(sender_id, names_dict):
        return names_dict.get(sender_id, sender_id or "我")

    # 获取所有会话
    session_db = cache.get(os.path.join("session", "session.db"))
    if not session_db:
        click.echo("  错误: 无法解密 session.db", err=True)
        return

    with closing(sqlite3.connect(session_db)) as conn:
        rows = conn.execute("""
            SELECT username, last_timestamp
            FROM SessionTable
            WHERE last_timestamp > 0
            ORDER BY last_timestamp DESC
            LIMIT ?
        """, (max_chats,)).fetchall()

    total = len(rows)
    click.echo(f"  [1/2] 找到 {total} 个会话")

    if total == 0:
        click.echo("  没有找到任何会话")
        return

    # 账号输出目录
    account_output_dir = output_dir / wxid
    account_output_dir.mkdir(parents=True, exist_ok=True)

    exported = 0
    failed = 0

    click.echo("  [2/2] 开始导出...")

    for i, (username, ts) in enumerate(rows, 1):
        display_name = names.get(username, username)

        # 清理显示名称(用于文件名)
        safe_name = display_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        chat_dir = account_output_dir / safe_name

        click.echo(f"    [{i}/{total}] {display_name}")

        try:
            # 解析聊天上下文
            chat_ctx = resolve_chat_context(username, msg_db_keys, cache, decrypted_dir)
            debug_log(f"resolve_chat_context({username}) = {chat_ctx}")
            if not chat_ctx:
                click.echo(f"      跳过: resolve_chat_context 返回 None")
                continue
            if not chat_ctx.get('db_path'):
                debug_log(f"chat_ctx keys: {list(chat_ctx.keys())}")
                click.echo(f"      跳过: db_path 为 None, message_tables={len(chat_ctx.get('message_tables', []))}")
                continue

            # 创建聊天目录
            chat_dir.mkdir(parents=True, exist_ok=True)

            # 收集消息详情
            messages = _collect_message_details(
                chat_ctx, names, display_name_fn,
                start_ts=start_ts, end_ts=end_ts, limit=limit,
                db_dir=db_dir
            )

            if not messages:
                click.echo(f"      跳过: 无消息")
                continue

            # 生成 HTML
            html_content = _generate_html(
                chat_ctx['display_name'],
                chat_ctx['is_group'],
                start_time or "最早",
                end_time or "最新",
                messages,
            )

            # 写入 HTML 文件
            html_path = chat_dir / "index.html"
            html_path.write_text(html_content, encoding="utf-8")

            # 生成 Markdown
            md_content = _generate_markdown(
                chat_ctx['display_name'],
                chat_ctx['is_group'],
                start_time or "最早",
                end_time or "最新",
                messages,
            )

            # 写入 Markdown 文件
            md_path = chat_dir / "index.md"
            md_path.write_text(md_content, encoding="utf-8")

            exported += 1

        except Exception as e:
            click.echo(f"      失败: {e}")
            failed += 1

    click.echo("")
    click.echo(f"  成功: {exported} 个聊天")
    click.echo(f"  失败: {failed} 个聊天")