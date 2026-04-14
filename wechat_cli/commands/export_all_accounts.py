"""export-all-accounts 命令 - 导出所有账号的聊天记录"""

import click
import os
import json
from contextlib import closing
from pathlib import Path
from datetime import datetime

from ..core.config import ACCOUNTS_DIR, ACCOUNTS_INDEX_FILE, list_accounts, load_account_config
from ..core.db_cache import DBCache
from ..core.contacts import get_contact_names
from ..core.messages import resolve_chat_context, collect_chat_history, parse_time_range


@click.command("export-all-accounts")
@click.option("--output", "output_path", default=None, help="输出目录路径")
@click.option("--limit", default=2000, help="每个聊天导出的消息数量")
@click.option("--max-chats", default=100, help="每个账号最多导出多少个聊天")
@click.option("--start-time", default=None, help="开始时间 (YYYY-MM-DD)")
@click.option("--end-time", default=None, help="结束时间 (YYYY-MM-DD)")
@click.option("--debug", is_flag=True, help="显示详细调试信息")
def export_all_accounts(output_path, limit, max_chats, start_time, end_time, debug):
    """导出所有账号的聊天记录为 HTML 页面（纯文字版）

    \b
    示例:
      wechat-cli export-all-accounts                     # 导出到 ~/wechat-chats-backup/
      wechat-cli export-all-accounts --output ~/backup   # 导出到指定目录
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
        click.echo(f"  ACCOUNTS_DIR: {ACCOUNTS_DIR}")
        click.echo(f"  ACCOUNTS_INDEX_FILE: {ACCOUNTS_INDEX_FILE}")
        click.echo(f"  文件是否存在: {os.path.exists(ACCOUNTS_INDEX_FILE)}")
        if os.path.exists(ACCOUNTS_INDEX_FILE):
            try:
                data = json.load(open(ACCOUNTS_INDEX_FILE))
                click.echo(f"  文件内容: {json.dumps(data, indent=2)[:500]}")
            except Exception as e:
                click.echo(f"  读取失败: {e}")
        click.echo("")
        click.echo("解决方法:")
        click.echo("  1. 确保微信已登录且数据已解密")
        click.echo("  2. 运行: wechat-cli init --all")
        ctx.exit(1)

    # 输出目录
    if output_path:
        output_dir = Path(output_path)
    else:
        output_dir = Path.home() / "wechat-chats-backup"

    output_dir.mkdir(parents=True, exist_ok=True)

    # 解析时间范围
    start_ts, end_ts = parse_time_range(start_time or '', end_time or '')

    click.echo("")
    click.echo("=" * 60)
    click.echo("  导出所有账号聊天记录（纯文字版）")
    click.echo("=" * 60)
    click.echo(f"账号数: {len(accounts)}")
    click.echo(f"输出目录: {output_dir}")
    click.echo("")

    for wxid in accounts:
        click.echo(f"\n[账号] {wxid}")
        click.echo("-" * 40)

        try:
            _export_account(wxid, output_dir, limit, max_chats, start_ts, end_ts, start_time, end_time, debug)
        except Exception as e:
            click.echo(f"  导出失败: {e}", err=True)
            if debug:
                import traceback
                traceback.print_exc()

    click.echo("")
    click.echo("=" * 60)
    click.echo("全部导出完成")
    click.echo("=" * 60)
    click.echo(f"输出目录: {output_dir}")
    click.echo("")
    click.echo("使用方法:")
    click.echo(f"  1. 打开文件夹: {output_dir}")
    click.echo("  2. 进入账号目录 → 聊天目录 → 双击 index.html")


def _export_account(wxid, output_dir, limit, max_chats, start_ts, end_ts, start_time, end_time, debug=False):
    """导出单个账号的所有聊天"""
    from .export_html import _generate_html, _generate_markdown

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

    # 查找所有 msg db
    msg_db_keys = [k for k in all_keys if 'message' in k.lower()]
    debug_log(f"msg_db_keys count = {len(msg_db_keys)}")
    debug_log(f"msg_db_keys sample: {msg_db_keys[:3]}...")

    # 获取联系人名称
    names = get_contact_names(cache, decrypted_dir)

    # 显示名函数
    def display_name_fn(username, names_dict):
        if not username:
            return ""
        name = names_dict.get(username, '')
        return name if name else username

    # 账号输出目录
    account_dir = output_dir / wxid
    account_dir.mkdir(parents=True, exist_ok=True)

    # 查找所有聊天
    click.echo(f"  [1/2] 查找聊天会话...")

    chats = []
    for db_key in msg_db_keys:
        db_path = cache.get(db_key)
        if not db_path or not os.path.exists(db_path):
            continue

        try:
            with closing(sqlite3.connect(db_path)) as conn:
                # 查找所有消息表
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
                ).fetchall()

                for (table_name,) in tables:
                    # 获取最新消息时间
                    try:
                        row = conn.execute(
                            f"SELECT MAX(create_time), COUNT(*) FROM [{table_name}]"
                        ).fetchone()
                        if row and row[1] > 0:
                            max_time = row[0]
                            count = row[1]
                            
                            # 获取聊天对象名
                            try:
                                sample = conn.execute(
                                    f"SELECT talker FROM [{table_name}] LIMIT 1"
                                ).fetchone()
                                chat_username = sample[0] if sample else table_name
                            except:
                                chat_username = table_name

                            display_name = display_name_fn(chat_username, names)
                            
                            chats.append({
                                'username': chat_username,
                                'display_name': display_name,
                                'db_path': db_path,
                                'table_name': table_name,
                                'max_time': max_time,
                                'count': count,
                            })
                    except:
                        pass
        except Exception as e:
            if debug:
                debug_log(f"读取 {db_key} 失败: {e}")

    # 排序（按最新消息时间）
    chats.sort(key=lambda x: x['max_time'], reverse=True)

    click.echo(f"  找到 {len(chats)} 个会话")

    if len(chats) > max_chats:
        click.echo(f"  只导出前 {max_chats} 个（--max-chats 限制）")
        chats = chats[:max_chats]

    # 导出
    click.echo(f"  [2/2] 开始导出...")

    exported = 0
    failed = 0

    for i, chat_info in enumerate(chats, 1):
        chat_name = chat_info['display_name'] or chat_info['username']
        click.echo(f"    [{i}/{len(chats)}] {chat_name}")

        try:
            # 解析聊天上下文
            chat_ctx = resolve_chat_context(
                chat_info['username'],
                msg_db_keys,
                cache,
                decrypted_dir
            )

            if not chat_ctx or not chat_ctx.get('db_path'):
                click.echo(f"      跳过: resolve_chat_context 返回 None")
                continue

            # 创建聊天目录
            safe_name = chat_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            chat_dir = account_dir / safe_name
            chat_dir.mkdir(parents=True, exist_ok=True)

            # 收集消息（使用已有函数）
            lines, failures = collect_chat_history(
                chat_ctx, names, display_name_fn,
                start_ts=start_ts, end_ts=end_ts, limit=limit, offset=0,
            )

            if not lines:
                click.echo(f"      跳过: 无消息")
                continue

            # 转换为 messages 格式
            messages = []
            for line in lines:
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    time_str = parts[0]
                    rest = parts[1] + ' ' + parts[2]
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
                chat_name,
                chat_ctx.get('is_group', False),
                start_time or "最早",
                end_time or "最新",
                messages,
            )

            html_path = chat_dir / "index.html"
            html_path.write_text(html_content, encoding="utf-8")

            # 生成 Markdown
            md_content = _generate_markdown(
                chat_name,
                chat_ctx.get('is_group', False),
                start_time or "最早",
                end_time or "最新",
                messages,
            )

            md_path = chat_dir / "index.md"
            md_path.write_text(md_content, encoding="utf-8")

            exported += 1

        except Exception as e:
            click.echo(f"      失败: {e}")
            failed += 1
            if debug:
                import traceback
                traceback.print_exc()

    click.echo("")
    click.echo(f"  成功: {exported} 个聊天")
    click.echo(f"  失败: {failed} 个聊天")


import sqlite3