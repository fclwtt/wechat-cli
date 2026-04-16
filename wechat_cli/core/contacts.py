"""联系人管理 — 加载、缓存、模糊匹配

注意：移除全局变量，避免多账号时数据串用
"""

import os
import re
import sqlite3


def _load_contacts_from(db_path):
    """从 contact.db 加载联系人"""
    names = {}
    full = []
    conn = sqlite3.connect(db_path)
    try:
        for r in conn.execute("SELECT username, nick_name, remark FROM contact").fetchall():
            uname, nick, remark = r
            display = remark if remark else nick if nick else uname
            names[uname] = display
            full.append({'username': uname, 'nick_name': nick or '', 'remark': remark or ''})
    finally:
        conn.close()
    return names, full


def get_contact_names(cache, decrypted_dir):
    """获取联系人名称字典
    
    Args:
        cache: DBCache 对象，用于解密数据库
        decrypted_dir: 预解密目录
        
    Returns:
        dict: {username: display_name}
        
    注意：不再使用全局缓存，每次调用都重新加载
    （避免多账号时数据串用）
    """
    # 优先使用预解密文件
    pre_decrypted = os.path.join(decrypted_dir, "contact", "contact.db")
    if os.path.exists(pre_decrypted):
        try:
            names, _ = _load_contacts_from(pre_decrypted)
            return names
        except Exception:
            pass

    # 使用 cache 解密
    path = cache.get(os.path.join("contact", "contact.db"))
    if path:
        try:
            names, _ = _load_contacts_from(path)
            return names
        except Exception:
            pass

    return {}


def get_contact_full(cache, decrypted_dir):
    """获取联系人完整信息列表"""
    pre_decrypted = os.path.join(decrypted_dir, "contact", "contact.db")
    if os.path.exists(pre_decrypted):
        try:
            _, full = _load_contacts_from(pre_decrypted)
            return full
        except Exception:
            pass

    path = cache.get(os.path.join("contact", "contact.db"))
    if path:
        try:
            _, full = _load_contacts_from(path)
            return full
        except Exception:
            pass

    return []


def resolve_username(chat_name, cache, decrypted_dir):
    """根据显示名反查 username"""
    names = get_contact_names(cache, decrypted_dir)
    if chat_name in names or chat_name.startswith('wxid_') or '@chatroom' in chat_name:
        return chat_name
    chat_lower = chat_name.lower()
    for uname, display in names.items():
        if chat_lower == display.lower():
            return uname
    for uname, display in names.items():
        if chat_lower in display.lower():
            return uname
    return None


def get_self_username(db_dir, cache, decrypted_dir):
    """获取账号自己的 username"""
    if not db_dir:
        return ''
    names = get_contact_names(cache, decrypted_dir)
    account_dir = os.path.basename(os.path.dirname(db_dir))
    candidates = [account_dir]
    m = re.fullmatch(r'(.+)_([0-9a-fA-F]{4,})', account_dir)
    if m:
        candidates.insert(0, m.group(1))
    for candidate in candidates:
        if candidate and candidate in names:
            return candidate
    return ''


def get_group_members(chatroom_username, cache, decrypted_dir):
    """获取群聊成员列表。

    通过 contact.db 的 chatroom_member 关联表查询。

    Returns:
        dict: {'members': [...], 'owner': str}
        每个 member: {'username': ..., 'nick_name': ..., 'remark': ..., 'display_name': ...}
    """
    pre_decrypted = os.path.join(decrypted_dir, "contact", "contact.db")
    if os.path.exists(pre_decrypted):
        db_path = pre_decrypted
    else:
        db_path = cache.get(os.path.join("contact", "contact.db"))

    if not db_path:
        return {'members': [], 'owner': ''}

    names = get_contact_names(cache, decrypted_dir)
    conn = sqlite3.connect(db_path)
    try:
        # 1. 找到 chatroom 的 contact.id
        row = conn.execute("SELECT id FROM contact WHERE username = ?", (chatroom_username,)).fetchone()
        if not row:
            return {'members': [], 'owner': ''}
        room_id = row[0]

        # 2. 获取群主
        owner = ''
        owner_row = conn.execute("SELECT owner FROM chat_room WHERE id = ?", (room_id,)).fetchone()
        if owner_row and owner_row[0]:
            owner = names.get(owner_row[0], owner_row[0])

        # 3. 获取成员 ID 列表
        member_ids = [r[0] for r in conn.execute(
            "SELECT member_id FROM chatroom_member WHERE room_id = ?", (room_id,)
        ).fetchall()]
        if not member_ids:
            return {'members': [], 'owner': owner}

        # 4. 批量查询成员信息
        placeholders = ','.join('?' * len(member_ids))
        members = []
        for uid, username, nick, remark in conn.execute(
            f"SELECT id, username, nick_name, remark FROM contact WHERE id IN ({placeholders})",
            member_ids
        ):
            display = remark if remark else nick if nick else username
            members.append({
                'username': username,
                'nick_name': nick or '',
                'remark': remark or '',
                'display_name': display,
            })

        # 按 display_name 排序，群主排最前
        members.sort(key=lambda m: (0 if m['username'] == (owner_row[0] if owner_row else '') else 1, m['display_name']))

        return {'members': members, 'owner': owner}
    finally:
        conn.close()


def get_contact_detail(username, cache, decrypted_dir):
    """获取联系人详情。

    Returns:
        dict or None: 联系人详细信息
    """
    pre_decrypted = os.path.join(decrypted_dir, "contact", "contact.db")
    if os.path.exists(pre_decrypted):
        db_path = pre_decrypted
    else:
        db_path = cache.get(os.path.join("contact", "contact.db"))
    if not db_path:
        return None

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT username, nick_name, remark, alias, description, "
            "small_head_url, big_head_url, verify_flag, local_type "
            "FROM contact WHERE username = ?",
            (username,)
        ).fetchone()
        if not row:
            return None
        uname, nick, remark, alias, desc, small_url, big_url, verify, ltype = row
        return {
            'username': uname,
            'nick_name': nick or '',
            'remark': remark or '',
            'alias': alias or '',
            'description': desc or '',
            'avatar': small_url or big_url or '',
            'verify_flag': verify or 0,
            'local_type': ltype,
            'is_group': '@chatroom' in uname,
            'is_subscription': uname.startswith('gh_'),
        }
    finally:
        conn.close()


def display_name_for_username(username, names, db_dir, cache, decrypted_dir):
    """获取 username 的显示名"""
    if not username:
        return ''
    if username == get_self_username(db_dir, cache, decrypted_dir):
        # 返回自己的昵称，而不是 'me'
        return names.get(username, username)
    return names.get(username, username)