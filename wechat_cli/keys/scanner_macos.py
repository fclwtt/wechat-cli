"""macOS 密钥提取 — 通过 C 二进制扫描微信进程内存"""

import os
import platform
import subprocess
import sys
import tempfile

from .common import collect_db_files, cross_verify_keys, save_results, scan_memory_for_keys

# Entitlements needed for task_for_pid to work on WeChat
_ENTITLEMENTS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.get-task-allow</key>
    <true/>
</dict>
</plist>
"""


def _find_binary():
    """查找对应架构的 C 二进制。"""
    machine = platform.machine()
    if machine == "arm64":
        name = "find_all_keys_macos.arm64"
    elif machine == "x86_64":
        name = "find_all_keys_macos.x86_64"
    else:
        raise RuntimeError(f"不支持的 macOS 架构: {machine}")

    # PyInstaller 运行时：从临时解压目录查找
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    bin_path = os.path.join(base, "wechat_cli", "bin", name)
    if os.path.isfile(bin_path):
        return bin_path

    # fallback: 直接在 bin/ 下
    bin_path = os.path.join(base, "bin", name)
    if os.path.isfile(bin_path):
        return bin_path

    raise RuntimeError(
        f"找不到密钥提取二进制: {bin_path}\n"
        "请确认安装包完整"
    )


def _resign_wechat():
    """Re-sign WeChat with get-task-allow entitlement so task_for_pid works."""
    wechat_paths = [
        "/Applications/WeChat.app",
        os.path.expanduser("~/Applications/WeChat.app"),
    ]
    wechat_app = None
    for p in wechat_paths:
        if os.path.isdir(p):
            wechat_app = p
            break

    if wechat_app is None:
        return False, "未找到 WeChat.app（已搜索 /Applications 和 ~/Applications）"

    # Write entitlements to temp file
    ent_fd, ent_path = tempfile.mkstemp(suffix=".xml")
    try:
        with os.fdopen(ent_fd, "w") as f:
            f.write(_ENTITLEMENTS_XML)

        print(f"\n[*] 检测到 task_for_pid 权限不足，正在对微信重新签名...")
        print(f"    目标: {wechat_app}")

        result = subprocess.run(
            ["codesign", "--force", "--sign", "-", "--entitlements", ent_path, wechat_app],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        os.unlink(ent_path)

    if result.returncode != 0:
        return False, f"codesign 失败: {result.stderr.strip()}"

    print("[+] 签名完成！请重新启动微信后再执行 init。")
    return True, None


def extract_keys(db_dir, output_path, pid=None):
    """通过 C 二进制提取 macOS 微信数据库密钥。

    C 二进制需要在微信数据目录的父目录下运行，
    因为它会自动检测 db_storage 子目录。
    输出 all_keys.json 到当前工作目录。

    Args:
        db_dir: 微信 db_storage 目录
        output_path: all_keys.json 输出路径
        pid: 未使用（C 二进制自动检测进程）

    Returns:
        dict: salt_hex -> enc_key_hex 映射
    """
    import json

    binary = _find_binary()

    # C 二进制的工作目录需要是 db_storage 的父目录
    work_dir = os.path.dirname(db_dir)
    if not os.path.isdir(work_dir):
        raise RuntimeError(f"微信数据目录不存在: {work_dir}")

    print(f"[+] 使用 C 二进制提取密钥: {binary}")
    print(f"[+] 工作目录: {work_dir}")

    try:
        result = subprocess.run(
            [binary],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("密钥提取超时（120s）")
    except PermissionError:
        raise RuntimeError(
            f"无法执行 {binary}\n"
            "请确保文件有执行权限: chmod +x " + binary
        )

    # 打印 C 二进制的输出
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # 检测 task_for_pid 失败 → 尝试 re-sign
    combined_output = (result.stdout or "") + (result.stderr or "")
    if "task_for_pid" in combined_output:
        print("\n[!] task_for_pid 失败：macOS 安全策略阻止了进程内存访问。")
        print("[!] 需要对微信重新签名以允许调试访问。")

        ok, err = _resign_wechat()
        if ok:
            raise RuntimeError(
                "已对微信重新签名。请执行以下步骤后重试：\n"
                "  1. 退出微信（完全退出，不是最小化）\n"
                "  2. 重新打开微信并登录\n"
                "  3. 再次执行: sudo wechat-cli init"
            )
        else:
            raise RuntimeError(
                f"自动签名失败: {err}\n"
                "请手动执行以下命令后重试：\n"
                '  codesign --force --sign - --entitlements /dev/stdin /Applications/WeChat.app <<\'EOF\'\n'
                + _ENTITLEMENTS_XML +
                "EOF\n"
                "然后重启微信，再执行: sudo wechat-cli init"
            )

    # C 二进制输出 all_keys.json 到 work_dir
    c_output = os.path.join(work_dir, "all_keys.json")
    if not os.path.exists(c_output):
        raise RuntimeError(
            "C 二进制未能生成密钥文件。\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # 读取并转存到 output_path
    with open(c_output, encoding="utf-8") as f:
        keys_data = json.load(f)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(keys_data, f, indent=2, ensure_ascii=False)

    # 清理 C 二进制的临时输出
    if os.path.abspath(c_output) != os.path.abspath(output_path):
        os.remove(c_output)

    # 构建 salt -> key 映射
    key_map = {}
    for rel, info in keys_data.items():
        if isinstance(info, dict) and "enc_key" in info and "salt" in info:
            key_map[info["salt"]] = info["enc_key"]

    print(f"\n[+] 提取到 {len(key_map)} 个密钥，保存到: {output_path}")
    return key_map
