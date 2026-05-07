"""export-all-accounts 命令 - 导出所有账号的聊天记录"""

import click
import os
import json
import re
import sys
from contextlib import closing
from pathlib import Path
from datetime import datetime

# Windows 强制 UTF-8（Python 3.7+ 环境变量方式）
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# 安全输出函数：直接用 sys.stdout，绕过 Click 的编码机制
def safe_echo(msg, err=False):
    """安全输出，绕过 Click 直接用 sys.stdout"""
    import sys as _sys
    target = _sys.stderr if err else _sys.stdout
    try:
        target.write(msg + '\n')
        target.flush()
    except UnicodeEncodeError:
        # Windows CMD fallback：移除 emoji
        import re
        clean_msg = re.sub(r'[\U00010000-\U0010ffff]', '', msg)
        target.write(clean_msg + '\n')
        target.flush()

from ..core.config import ACCOUNTS_DIR, ACCOUNTS_INDEX_FILE, list_accounts, load_account_config
from ..core.db_cache import DBCache
from ..core.contacts import get_contact_names, get_self_username, get_contact_detail
from ..core.messages import resolve_chat_context, collect_chat_history, parse_time_range


@click.command("export-all-accounts")
@click.option("--output", "output_path", default=None, help="输出目录路径")
@click.option("--limit", default=None, help="每个聊天导出的消息数量（默认无限制）")
@click.option("--max-chats", default=None, help="每个账号最多导出多少个聊天（默认无限制）")
@click.option("--start-time", default=None, help="开始时间 (YYYY-MM-DD)")
@click.option("--end-time", default=None, help="结束时间 (YYYY-MM-DD)")
@click.option("--only-active", is_flag=True, help="只导出指定时间范围内有消息的聊天")
@click.option("--active-since", default=None, help="筛选指定日期有消息的聊天，但导出全部历史 (YYYY-MM-DD)，如 --active-since 2026-04-15")
@click.option("--daily", is_flag=True, help="每日导出模式：自动计算昨天日期，等同于 --active-since YESTERDAY")
@click.option("--index-file", default=None, help="索引文件路径，记录导出的聊天列表")
@click.option("--skip-existing", is_flag=True, help="跳过已存在的聊天（HTML 文件已存在则不重新生成）")
@click.option("--debug", is_flag=True, help="显示详细调试信息")
def export_all_accounts(output_path, limit, max_chats, start_time, end_time, only_active, active_since, daily, index_file, skip_existing, debug):
    """导出所有账号的聊天记录为 HTML 页面（纯文字版）

    \b
    示例:
      wechat-cli export-all-accounts                     # 导出到 ~/wechat-chats-backup/
      wechat-cli export-all-accounts --output ~/backup   # 导出到指定目录
      wechat-cli export-all-accounts --start-time 2026-04-12 --end-time 2026-04-12  # 导出指定日期的消息
      wechat-cli export-all-accounts --active-since 2026-04-15  # 筛选昨天有消息的聊天，导出全部历史
      wechat-cli export-all-accounts --debug             # 显示调试信息
    """
    # 调试输出函数
    def debug_log(msg):
        if debug:
            click.echo(f"[DEBUG] {msg}")

    # 处理 --daily 参数：自动计算昨天日期
    if daily:
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        active_since = yesterday
        click.echo(f"[DAILY] 自动计算昨天日期: {yesterday}")
    
    debug_log(f"ACCOUNTS_DIR = {ACCOUNTS_DIR}")
    debug_log(f"ACCOUNTS_INDEX_FILE = {ACCOUNTS_INDEX_FILE}")
    debug_log(f"accounts index exists = {os.path.exists(ACCOUNTS_INDEX_FILE)}")

    # 获取所有账号（去重，防止 accounts.json 有重复）
    accounts = list(set(list_accounts()))
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
        # Windows 默认路径
        output_dir = Path(r"E:\共享文件夹\wechat-chats-backup")

    output_dir.mkdir(parents=True, exist_ok=True)

    # 处理 --daily 模式的索引文件：自动生成路径
    if daily and not index_file:
        index_dir = output_dir / "daily-index"
        index_dir.mkdir(parents=True, exist_ok=True)
        index_file = str(index_dir / f"{active_since}.txt")
        click.echo(f"[DAILY] 索引文件: {index_file}")
    
    # 全量导出也生成索引
    if not daily and not index_file:
        index_dir = output_dir / "export-index"
        index_dir.mkdir(parents=True, exist_ok=True)
        from datetime import date
        index_file = str(index_dir / f"{date.today().strftime('%Y-%m-%d')}.txt")
        click.echo(f"[EXPORT] 索引文件: {index_file}")

    # 解析时间范围（用于导出消息的时间过滤）
    start_ts, end_ts = parse_time_range(start_time or '', end_time or '')
    
    # 解析 active-since 时间范围（用于筛选聊天，不限制导出时间）
    active_since_ts, _ = parse_time_range(active_since or '', active_since or '') if active_since else (None, None)

    click.echo("")
    click.echo("=" * 60)
    click.echo("  导出所有账号聊天记录（纯文字版）")
    click.echo("=" * 60)
    click.echo(f"账号数: {len(accounts)}")
    click.echo(f"输出目录: {output_dir}")
    click.echo("")

    for wxid in accounts:
        try:
            account_folder_name = _export_account(wxid, output_dir, limit, max_chats, start_ts, end_ts, start_time, end_time, only_active, active_since, active_since_ts, index_file, debug)
            click.echo(f"\n[账号] {account_folder_name}")
            click.echo("-" * 40)
        except Exception as e:
            safe_echo(f"\n[账号] {wxid} - 导出失败: {e}", err=True)
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
    click.echo("  2. 进入账号目录 → 聊天目录 → 双击聊天名.html")


def _export_account(wxid, output_dir, limit, max_chats, start_ts, end_ts, start_time, end_time, only_active=False, active_since=None, active_since_ts=None, index_file=None, debug=False):
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

    # 初始化 cache（使用固定解密目录）
    cache = DBCache(all_keys, db_dir, decrypted_dir)
    debug_log(f"缓存目录: {cache.CACHE_DIR}")

    debug_log(f"cache initialized")

    # 查找所有 msg db
    msg_db_keys = [k for k in all_keys if 'message' in k.lower()]
    debug_log(f"msg_db_keys count = {len(msg_db_keys)}")
    debug_log(f"msg_db_keys sample: {msg_db_keys[:3]}...")

    # 获取联系人名称
    import time
    names_start = time.time()
    names = get_contact_names(cache, decrypted_dir)
    names_time = time.time() - names_start
    if names_time > 0.5:
        debug_log(f"[慢] 加载联系人耗时: {names_time:.2f}s ({len(names)} 个)")

    # 获取账号自己的 username
    self_username = get_self_username(db_dir, cache, decrypted_dir)
    debug_log(f"账号自己的 username: {self_username}")
    # 获取自己的昵称
    self_display_name = names.get(self_username, self_username) if self_username else ''
    debug_log(f"账号自己的昵称: {self_display_name}")

    # 显示名函数
    def display_name_fn(username, names_dict):
        if not username:
            return ""
        name = names_dict.get(username, '')
        return name if name else username

    # 账号输出目录（用昵称显示，加 wxid 后缀避免重名）
    account_folder_name = f"{self_display_name}_{wxid}" if self_display_name else wxid
    account_dir = output_dir / account_folder_name
    account_dir.mkdir(parents=True, exist_ok=True)

    # 查找所有聊天
    click.echo(f"  [1/2] 查找聊天会话...")

    # 先构建 username -> MD5 hash 映射
    import hashlib
    username_to_hash = {}
    hash_to_username = {}
    for uname in names.keys():
        h = hashlib.md5(uname.encode()).hexdigest()
        username_to_hash[uname] = h
        hash_to_username[h] = uname

    debug_log(f"联系人数量: {len(names)}")

    # 尝试从 session.db 获取会话列表（补充 hash_to_username 和昵称）
    session_start = time.time()
    session_db_key = os.path.join("session", "session.db")
    session_db_path = cache.get(session_db_key)
    if session_db_path:
        try:
            session_open_time = time.time() - session_start
            if session_open_time > 0.5:
                debug_log(f"[慢] 解密 session.db 耗时: {session_open_time:.2f}s")
            
            with closing(sqlite3.connect(session_db_path)) as conn:
                # 先探测 SessionTable 的实际列名
                columns = [col[1] for col in conn.execute("PRAGMA table_info(SessionTable)").fetchall()]
                debug_log(f"SessionTable 列名: {columns}")
                
                # 尝试找到存储聊天名称的列
                # 只用真正的名称列，不用 last_sender_display_name
                # last_sender_display_name 是最后发送者的名字，不稳定且不准确
                name_column = None
                for candidate in ['nickname', 'display_name', 'name', 'nick_name']:
                    if candidate in columns:
                        name_column = candidate
                        break
                
                if 'username' not in columns:
                    debug_log("SessionTable 没有 username 列，跳过")
                elif name_column:
                    debug_log(f"使用列: username, {name_column}")
                    session_rows = conn.execute(
                        f"SELECT username, {name_column} FROM SessionTable"
                    ).fetchall()
                    debug_log(f"SessionTable 会话数: {len(session_rows)}")
                    for uname, display_name in session_rows:
                        if uname and uname not in names:
                            # 补充到 names
                            names[uname] = display_name if display_name else uname
                            h = hashlib.md5(uname.encode()).hexdigest()
                            hash_to_username[h] = uname
                        elif uname and display_name and names.get(uname) == uname:
                            # 如果已有 username 作为显示名，用显示名替换
                            names[uname] = display_name
                else:
                    debug_log("SessionTable 没有名称列，只补充 username 到 hash 映射")
                    session_rows = conn.execute(
                        "SELECT username FROM SessionTable"
                    ).fetchall()
                    for uname in session_rows:
                        uname = uname[0]
                        if uname:
                            h = hashlib.md5(uname.encode()).hexdigest()
                            hash_to_username[h] = uname
                            if uname not in names:
                                names[uname] = uname
                    session_rows = conn.execute("SELECT username FROM SessionTable").fetchall()
                    for (uname,) in session_rows:
                        if uname:
                            h = hashlib.md5(uname.encode()).hexdigest()
                            hash_to_username[h] = uname
                            if uname not in names:
                                names[uname] = uname  # 用 username 作为显示名
        except Exception as e:
            debug_log(f"读取 session.db 失败: {e}")

    debug_log(f"hash_to_username 总数: {len(hash_to_username)}")

    chats = []
    msg_scan_start = time.time()
    for db_key in msg_db_keys:
        db_path = cache.get(db_key)
        if not db_path or not os.path.exists(db_path):
            continue
        
        db_open_time = time.time() - msg_scan_start
        if db_open_time > 1.0:
            debug_log(f"[慢] 解密 {db_key} 耗时: {db_open_time:.2f}s")
        msg_scan_start = time.time()  # 重置计时

        try:
            with closing(sqlite3.connect(db_path)) as conn:
                # 查找所有消息表
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
                ).fetchall()

                for (table_name,) in tables:
                    # 从表名提取 hash (Msg_xxx)
                    table_hash = table_name.replace('Msg_', '')
                    
                    # 用 hash 反查 username
                    chat_username = hash_to_username.get(table_hash)
                    if not chat_username:
                        # 没找到匹配的联系人，跳过（无法识别身份）
                        debug_log(f"表 {table_name} hash={table_hash} 没匹配到联系人，跳过")
                        continue
                    
                    # 只保留私聊：wxid_ 开头或普通微信号（不含特殊标识）
                    # 排除：群聊(@chatroom)、公众号(gh_)、文件传输助手(filehelper)、系统账号(weixin等)
                    is_private_chat = False
                    if chat_username.startswith('wxid_'):
                        is_private_chat = True
                    elif '@chatroom' not in chat_username and not chat_username.startswith('gh_') and not chat_username.startswith('filehelper') and not chat_username.startswith('weixin'):
                        # 普通微信号格式（不含特殊标识）
                        is_private_chat = True
                    
                    if not is_private_chat:
                        debug_log(f"跳过非私聊: {chat_username}")
                        continue
                    
                    # 进一步检查：查询 local_type 和 verify_flag，排除服务号
                    contact_detail = get_contact_detail(chat_username, cache, decrypted_dir)
                    if contact_detail:
                        local_type = contact_detail.get('local_type', 0)
                        verify_flag = contact_detail.get('verify_flag', 0)
                        # local_type != 1 → 不是个人联系人，跳过
                        # verify_flag > 0 → 认证账号（服务号），跳过
                        if local_type != 1 or verify_flag > 0:
                            debug_log(f"跳过服务号: {chat_username} (local_type={local_type}, verify_flag={verify_flag})")
                            continue

                    # 获取最新消息时间
                    try:
                        row = conn.execute(
                            f"SELECT MAX(create_time), COUNT(*) FROM [{table_name}]"
                        ).fetchone()
                        if row and row[1] > 0:
                            max_time = row[0]
                            count = row[1]
                            
                            # 如果指定了 --only-active，检查时间范围内是否有消息
                            if only_active and start_ts and end_ts:
                                active_row = conn.execute(
                                    f"SELECT COUNT(*) FROM [{table_name}] WHERE create_time >= ? AND create_time <= ?",
                                    [start_ts, end_ts]
                                ).fetchone()
                                active_count = active_row[0] if active_row else 0
                                if active_count == 0:
                                    # 时间范围内无消息，跳过
                                    debug_log(f"跳过 {table_name}: 时间范围内无消息")
                                    continue
                                debug_log(f"{table_name}: 时间范围内有 {active_count} 条消息")
                            
                            # 如果指定了 --active-since，检查该日期是否有消息（筛选聊天，不限制导出时间）
                            if active_since_ts:
                                # 一天的时间范围：从 active_since_ts 到 active_since_ts + 86400
                                active_row = conn.execute(
                                    f"SELECT COUNT(*) FROM [{table_name}] WHERE create_time >= ? AND create_time <= ?",
                                    [active_since_ts, active_since_ts + 86400]
                                ).fetchone()
                                active_count = active_row[0] if active_row else 0
                                if active_count == 0:
                                    # 该日期无消息，跳过
                                    debug_log(f"跳过 {table_name}: --active-since 日期内无消息")
                                    continue
                                debug_log(f"{table_name}: --active-since 日期内有 {active_count} 条消息")
                            
                            display_name = display_name_fn(chat_username, names)
                            
                            # 检查是否已存在（去重，防止同一 username 多个 Msg 表）
                            existing = [c for c in chats if c['username'] == chat_username]
                            if existing:
                                # 已存在，合并消息数和更新时间
                                old = existing[0]
                                old['count'] += count
                                if max_time > old['max_time']:
                                    old['max_time'] = max_time
                                    old['db_path'] = db_path
                                    old['table_name'] = table_name
                                debug_log(f"合并 {table_name}: {chat_username} 已存在，合并消息数")
                            else:
                                chats.append({
                                    'username': chat_username,
                                    'display_name': display_name,
                                    'db_path': db_path,
                                    'table_name': table_name,
                                    'max_time': max_time,
                                    'count': count,
                                })
                    except Exception as e:
                        if debug:
                            debug_log(f"查询 {table_name} 失败: {e}")
        except Exception as e:
            if debug:
                debug_log(f"读取 {db_key} 失败: {e}")

    # 排序（按最新消息时间）
    chats.sort(key=lambda x: x['max_time'], reverse=True)

    click.echo(f"  找到 {len(chats)} 个会话")

    if max_chats and len(chats) > max_chats:
        click.echo(f"  只导出前 {max_chats} 个（--max-chats 限制）")
        chats = chats[:max_chats]

    # 导出
    click.echo(f"  [2/2] 开始导出...")

    exported = 0
    failed = 0
    exported_chats = []  # 记录导出的聊天文件夹名
    
    # 性能分析
    import time
    export_times = []

    for i, chat_info in enumerate(chats, 1):
        chat_start = time.time()
        
        chat_name = chat_info['display_name'] or chat_info['username']
        # 如果 display_name 是表名(Msg_xxx)，显示 username
        if chat_name.startswith('Msg_'):
            chat_name = chat_info['username'] if not chat_info['username'].startswith('Msg_') else chat_name
        safe_echo(f"    [{i}/{len(chats)}] {chat_name}")

        try:
            step_start = time.time()
            
            # 直接构建聊天上下文（已有 db_path 和 table_name）
            chat_ctx = {
                'query': chat_info['username'],
                'username': chat_info['username'],
                'display_name': chat_info['display_name'],
                'db_path': chat_info['db_path'],
                'table_name': chat_info['table_name'],
                'message_tables': [{'db_path': chat_info['db_path'], 'table_name': chat_info['table_name']}],
                'is_group': '@chatroom' in chat_info['username'],
                'self_username': self_username,
            }

            # 创建聊天目录（用 wxid 作为文件夹名，避免特殊字符导致 Syncthing 同步失败）
            folder_name = chat_info['username']  # 直接用 wxid
            chat_dir = account_dir / folder_name
            
            # 如果指定了 --skip-existing，检查 HTML 文件是否已存在
            html_path = chat_dir / f"{folder_name}.html"
            if skip_existing and html_path.exists():
                safe_echo(f"      跳过: 已存在")
                continue
            
            chat_dir.mkdir(parents=True, exist_ok=True)

            # 收集消息（使用已有函数）
            # 如果用了 --active-since，不限制导出时间（导出全部历史）
            export_start_ts = None if active_since_ts else start_ts
            export_end_ts = None if active_since_ts else end_ts
            
            collect_start = time.time()
            lines, failures = collect_chat_history(
                chat_ctx, names, display_name_fn,
                start_ts=export_start_ts, end_ts=export_end_ts, limit=limit, offset=0,
            )
            collect_time = time.time() - collect_start
            if collect_time > 0.5:
                click.echo(f"      [慢] 收集消息耗时: {collect_time:.2f}s ({len(lines)} 条)")

            if not lines:
                click.echo(f"      跳过: 无消息")
                continue

            # 转换为 messages 格式
            convert_start = time.time()
            messages = []
            is_group_chat = chat_ctx.get('is_group', False)
            for line in lines:
                # line 格式: "[时间] 发送者: 内容" 或 "[时间] 内容"
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
                    # 自己的消息：发送者是 self_username 或 self_display_name（昵称）或 '我'
                    is_self = sender_part == self_username or sender_part == self_display_name or sender_part == '我'
                else:
                    # 没有发送者前缀（理论上不会再出现）
                    sender_part = ''
                    content = line_content
                    is_self = False
                
                messages.append({
                    'time': time_str,
                    'sender': sender_part,
                    'content': content,
                    'is_self': is_self,
                })
            convert_time = time.time() - convert_start
            if convert_time > 0.5:
                click.echo(f"      [慢] 转换消息耗时: {convert_time:.2f}s")

            # 生成 HTML
            # 如果用了 --active-since，时间显示为 "最早" 到 "最新"
            html_start_time = "最早" if active_since_ts else (start_time or "最早")
            html_end_time = "最新" if active_since_ts else (end_time or "最新")
            
            html_start = time.time()
            html_content = _generate_html(
                chat_name,
                chat_ctx.get('is_group', False),
                html_start_time,
                html_end_time,
                messages,
            )
            html_time = time.time() - html_start
            if html_time > 0.5:
                click.echo(f"      [慢] 生成HTML耗时: {html_time:.2f}s")

            html_path = chat_dir / f"{folder_name}.html"  # 用 wxid 作为文件名
            html_path.write_text(html_content, encoding="utf-8")

            # 生成 Markdown
            md_start = time.time()
            md_content = _generate_markdown(
                chat_name,
                chat_ctx.get('is_group', False),
                html_start_time,
                html_end_time,
                messages,
            )
            md_time = time.time() - md_start
            if md_time > 0.5:
                click.echo(f"      [慢] 生成MD耗时: {md_time:.2f}s")

            md_path = chat_dir / f"{folder_name}.md"  # 用 wxid 作为文件名
            md_path.write_text(md_content, encoding="utf-8")

            exported += 1
            
            # 获取联系人详情（备注名+昵称）
            contact_detail = get_contact_detail(chat_info['username'], cache, decrypted_dir)
            remark = contact_detail.get('remark', '') if contact_detail else ''
            nick_name = contact_detail.get('nick_name', '') if contact_detail else ''
            
            # 记录导出的聊天文件夹名（用于索引）
# 格式: 账号 | wxid | 备注名 | 昵称 | 消息数 | 最后消息时间
            last_msg_time = datetime.fromtimestamp(chat_info['max_time']).strftime('%Y-%m-%d %H:%M')
            exported_chats.append({
                'path': f"{account_folder_name}/{folder_name}",
                'wxid': chat_info['username'],
                'last_msg_time': last_msg_time,
                'count': chat_info['count'],
                'remark': remark,
                'nick_name': nick_name,
            })
            
            chat_total = time.time() - chat_start
            if chat_total > 1.0:
                safe_echo(f"      [慢] 总耗时: {chat_total:.2f}s")
            export_times.append(chat_total)

        except Exception as e:
            safe_echo(f"      失败: {e}")
            failed += 1
            if debug:
                import traceback
                traceback.print_exc()

    click.echo("")
    click.echo(f"  成功: {exported} 个聊天")
    click.echo(f"  失败: {failed} 个聊天")
    
    # 写入索引文件
    if index_file and exported_chats:
        index_path = Path(index_file)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        # 判断是否新文件
        is_new_file = not index_path.exists()
        mode = 'a' if index_path.exists() else 'w'
        with open(index_path, mode, encoding='utf-8') as f:
            # 新文件写入表头
            if is_new_file:
                f.write("# 导出索引 - " + datetime.now().strftime('%Y-%m-%d') + "\n")
                f.write("# 格式: 账号 | wxid | 备注名 | 昵称 | 消息数 | 最后消息时间\n")
                f.write("#" + "=" * 80 + "\n\n")
            for chat in exported_chats:
                remark_display = chat['remark'] if chat['remark'] else '(无备注)'
                nick_display = chat['nick_name'] if chat['nick_name'] else '(无昵称)'
                f.write(f"{account_folder_name} | {chat['wxid']} | {remark_display} | {nick_display} | {chat['count']}条 | {chat['last_msg_time']}\n")
        click.echo(f"  索引: {index_file} ({len(exported_chats)} 个聊天)")


    return account_folder_name
import sqlite3