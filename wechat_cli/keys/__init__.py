"""密钥提取模块 — 根据平台调用对应的 scanner"""

import platform
import os


def extract_keys(db_dir, output_path, pid=None):
    """提取微信数据库密钥并保存到 output_path。

    Args:
        db_dir: 微信数据库目录（db_storage）
        output_path: all_keys.json 输出路径
        pid: 可选，指定微信进程 PID（默认自动检测）

    Returns:
        dict: salt_hex -> enc_key_hex 的映射

    Raises:
        RuntimeError: 提取失败
    """
    system = platform.system().lower()
    if system == "darwin":
        from .scanner_macos import extract_keys as _extract
        return _extract(db_dir, output_path, pid=pid)
    elif system == "windows":
        from .scanner_windows import extract_keys as _extract
        return _extract(db_dir, output_path, pid=pid)
    elif system == "linux":
        from .scanner_linux import extract_keys as _extract
        return _extract(db_dir, output_path, pid=pid)
    else:
        raise RuntimeError(f"不支持的平台: {platform.system()}")


def extract_all_accounts_keys(output_base_dir):
    """提取所有微信账号的密钥。

    Args:
        output_base_dir: ~/.wechat-cli/accounts/ 目录

    Returns:
        list: [{"wxid": ..., "db_dir": ..., "keys_file": ...}, ...]
    """
    system = platform.system().lower()
    if system == "windows":
        from .scanner_windows import extract_all_accounts_keys as _extract_all
        return _extract_all(output_base_dir)
    else:
        # macOS/Linux 目前不支持多账号同时登录
        raise RuntimeError(f"多账号提取目前仅支持 Windows 平台")
