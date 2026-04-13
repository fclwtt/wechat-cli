"""init 命令 — 交互式初始化，提取密钥并生成配置"""

import json
import os
import sys

import click

from ..core.config import STATE_DIR, CONFIG_FILE, KEYS_FILE, auto_detect_db_dir, ACCOUNTS_DIR, ACCOUNTS_INDEX_FILE


@click.command()
@click.option("--db-dir", default=None, help="微信数据目录路径（默认自动检测）")
@click.option("--force", is_flag=True, help="强制重新提取密钥")
@click.option("--all", "all_accounts", is_flag=True, help="提取所有微信账号的密钥")
def init(db_dir, force, all_accounts):
    """初始化 wechat-cli：提取密钥并生成配置

    \b
    示例:
      wechat-cli init                    # 单账号初始化
      wechat-cli init --all              # 提取所有账号
      wechat-cli init --force            # 强制重新提取
    """
    # 多账号模式
    if all_accounts:
        return _init_all_accounts(force)
    
    # 单账号模式
    return _init_single_account(db_dir, force)


def _init_all_accounts(force):
    """初始化所有微信账号"""
    click.echo("WeChat CLI 多账号初始化")
    click.echo("=" * 40)
    
    # 创建账号目录
    os.makedirs(ACCOUNTS_DIR, exist_ok=True)
    
    # 提取所有账号密钥
    click.echo("\n开始提取所有账号密钥...")
    try:
        from ..keys import extract_all_accounts_keys
        accounts = extract_all_accounts_keys(ACCOUNTS_DIR)
    except RuntimeError as e:
        click.echo(f"\n[!] 密钥提取失败: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n[!] 密钥提取出错: {e}", err=True)
        sys.exit(1)
    
    if not accounts:
        click.echo("\n[!] 未找到任何微信账号", err=True)
        sys.exit(1)
    
    # 更新账号索引
    account_ids = [a["wxid"] for a in accounts]
    with open(ACCOUNTS_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(account_ids, f, indent=2)
    
    # 设置默认账号
    if account_ids:
        default_wxid = account_ids[0]
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"default_account": default_wxid}, f, indent=2)
    
    click.echo(f"\n[+] 初始化完成!")
    click.echo(f"    账号数: {len(accounts)}")
    for a in accounts:
        click.echo(f"    - {a['wxid']}: {a['key_count']} 个密钥")
    click.echo(f"    默认账号: {account_ids[0]}")
    click.echo(f"    账号目录: {ACCOUNTS_DIR}")
    click.echo("\n现在可以使用:")
    click.echo("  wechat-cli sessions")
    click.echo("  wechat-cli export-all-accounts")


def _init_single_account(db_dir, force):
    """初始化单个微信账号"""
    click.echo("WeChat CLI 初始化")
    click.echo("=" * 40)

    # 1. 检查是否已初始化
    if os.path.exists(CONFIG_FILE) and os.path.exists(KEYS_FILE) and not force:
        click.echo(f"已初始化（配置: {CONFIG_FILE}）")
        click.echo("使用 --force 重新提取密钥")
        return

    # 2. 创建状态目录
    os.makedirs(STATE_DIR, exist_ok=True)

    # 3. 确定 db_dir
    if db_dir is None:
        db_dir = auto_detect_db_dir()
        if db_dir is None:
            click.echo("[!] 未能自动检测到微信数据目录", err=True)
            click.echo("请通过 --db-dir 参数指定，例如:", err=True)
            click.echo("  wechat-cli init --db-dir ~/path/to/db_storage", err=True)
            sys.exit(1)
        click.echo(f"[+] 检测到微信数据目录: {db_dir}")
    else:
        db_dir = os.path.abspath(db_dir)
        if not os.path.isdir(db_dir):
            click.echo(f"[!] 目录不存在: {db_dir}", err=True)
            sys.exit(1)
        click.echo(f"[+] 使用指定数据目录: {db_dir}")

    # 4. 提取密钥
    click.echo("\n开始提取密钥...")
    try:
        from ..keys import extract_keys
        key_map = extract_keys(db_dir, KEYS_FILE)
    except RuntimeError as e:
        click.echo(f"\n[!] 密钥提取失败: {e}", err=True)
        if "sudo" not in str(e).lower():
            click.echo("提示: macOS/Linux 可能需要 sudo 权限", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n[!] 密钥提取出错: {e}", err=True)
        sys.exit(1)

    # 5. 写入配置
    cfg = {
        "db_dir": db_dir,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    click.echo(f"\n[+] 初始化完成!")
    click.echo(f"    配置: {CONFIG_FILE}")
    click.echo(f"    密钥: {KEYS_FILE}")
    click.echo(f"    提取到 {len(key_map)} 个数据库密钥")
    click.echo("\n现在可以使用:")
    click.echo("  wechat-cli sessions")
    click.echo("  wechat-cli history \"联系人\"")