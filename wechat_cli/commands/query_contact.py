"""查询联系人 - 独立脚本，支持多账号"""

import click
import os
import json
import sqlite3
from pathlib import Path

@click.command()
@click.option("--account", default=None, help="账号 wxid (如 tutou136589502_cf9f)")
@click.option("--query", default="", help="搜索关键词")
@click.option("--username", default=None, help="精确查询 username (如 wxid_xxx)")
def main(account, query, username):
    """查询联系人信息"""
    
    # 获取账号列表
    accounts_dir = Path.home() / ".wechat-cli" / "accounts"
    accounts_file = Path.home() / ".wechat-cli" / "accounts.json"
    
    if not accounts_file.exists():
        click.echo("错误: 未找到账号配置，请先运行 wechat-cli init --all", err=True)
        return
    
    accounts_data = json.load(open(accounts_file))
    accounts = list(set(accounts_data.get("accounts", [])))
    
    if not accounts:
        click.echo("错误: 账号列表为空", err=True)
        return
    
    # 如果没有指定账号，列出所有账号
    if not account:
        click.echo("可用账号:")
        for i, acc in enumerate(accounts, 1):
            click.echo(f"  {i}. {acc}")
        click.echo("\n使用 --account 选择账号")
        return
    
    # 加载账号配置
    acc_dir = accounts_dir / account
    keys_file = acc_dir / "keys.json"
    if not keys_file.exists():
        click.echo(f"错误: 账号 {account} 的密钥文件不存在", err=True)
        return
    
    keys_data = json.load(open(keys_file))
    
    # 找 db_dir
    accounts_info = accounts_data.get("accounts_info", {})
    acc_info = accounts_info.get(account, {})
    db_dir = acc_info.get("db_dir")
    
    if not db_dir:
        click.echo(f"错误: 账号 {account} 的 db_dir 不存在", err=True)
        return
    
    # 解密 contact.db
    decrypted_dir = acc_dir / "decrypted"
    decrypted_contact = decrypted_dir / "contact" / "contact.db"
    
    if not decrypted_contact.exists():
        click.echo(f"提示: contact.db 未解密，尝试在线解密...")
        # 这里可以加解密逻辑，暂时跳过
        click.echo(f"请先运行完整导出一次，会自动解密 contact.db")
        return
    
    # 查询 contact.db
    conn = sqlite3.connect(str(decrypted_contact))
    
    if username:
        # 精确查询
        row = conn.execute(
            "SELECT username, nick_name, remark, alias FROM contact WHERE username = ?",
            [username]
        ).fetchone()
        if row:
            uname, nick, remark, alias = row
            display = remark or nick or uname
            click.echo(f"\n联系人: {display}")
            click.echo(f"  username: {uname}")
            click.echo(f"  nick_name: {nick}")
            click.echo(f"  remark: {remark}")
            click.echo(f"  alias (微信号): {alias}")
        else:
            click.echo(f"未找到: {username}")
    elif query:
        # 搜索
        q_lower = query.lower()
        rows = conn.execute(
            "SELECT username, nick_name, remark, alias FROM contact "
            "WHERE LOWER(nick_name) LIKE ? OR LOWER(remark) LIKE ? OR LOWER(username) LIKE ?",
            [f"%{q_lower}%", f"%{q_lower}%", f"%{q_lower}%"]
        ).fetchall()
        
        click.echo(f"\n找到 {len(rows)} 个匹配:")
        for uname, nick, remark, alias in rows[:20]:
            display = remark or nick or uname
            click.echo(f"  {display}  (username: {uname})")
    else:
        # 统计
        count = conn.execute("SELECT COUNT(*) FROM contact").fetchone()[0]
        click.echo(f"\n联系人总数: {count}")
    
    conn.close()

if __name__ == "__main__":
    main()