"""微信图片解码 — .dat 文件转 JPG/PNG"""

import os
from pathlib import Path


# JPG 文件头
JPG_HEADER = bytes([0xFF, 0xD8, 0xFF])
# PNG 文件头
PNG_HEADER = bytes([0x89, 0x50, 0x4E, 0x47])


def decode_dat_file(dat_path, output_path=None, debug=False):
    """解码微信 .dat 图片文件

    Args:
        dat_path: .dat 文件路径
        output_path: 输出路径（可选，默认同名 .jpg）

    Returns:
        str: 解码后的图片路径，失败返回 None
    """
    if not os.path.exists(dat_path):
        if debug:
            print(f"      [decode] 文件不存在: {dat_path}")
        return None

    try:
        with open(dat_path, 'rb') as f:
            data = f.read()

        if debug:
            print(f"      [decode] 暴力破解: 文件大小={len(data)} bytes")
            print(f"      [decode] 暴力破解: 前10字节(hex): {data[:10].hex()}")

        if len(data) < 10:
            if debug:
                print(f"      [decode] 暴力破解: 文件太小")
            return None

        # 尝试不同的 XOR 密钥
        # 微信常见的 XOR 密钥在 0x00-0xFF 范围
        for xor_key in range(256):
            # 解码前3个字节
            decoded_header = bytes([b ^ xor_key for b in data[:3]])

            # 检查是否是 JPG 头
            if decoded_header == JPG_HEADER:
                # 找到了正确的 XOR 密钥
                decoded_data = bytes([b ^ xor_key for b in data])

                # 确定输出路径
                if output_path is None:
                    output_path = str(dat_path).replace('.dat', '.jpg')

                with open(output_path, 'wb') as f:
                    f.write(decoded_data)

                if debug:
                    print(f"      [decode] 暴力破解成功! XOR密钥=0x{xor_key:02X}")
                return output_path

            # 检查是否是 PNG 头（需要解码前4个字节）
            if len(data) >= 4:
                decoded_header4 = bytes([b ^ xor_key for b in data[:4]])
                if decoded_header4 == PNG_HEADER:
                    decoded_data = bytes([b ^ xor_key for b in data])

                    if output_path is None:
                        output_path = str(dat_path).replace('.dat', '.png')

                    with open(output_path, 'wb') as f:
                        f.write(decoded_data)

                    if debug:
                        print(f"      [decode] 暴力破解PNG成功! XOR密钥=0x{xor_key:02X}")
                    return output_path

        # 没找到正确的 XOR 密钥
        if debug:
            print(f"      [decode] 暴力破解失败: 所有256个密钥都不匹配")
        return None

    except Exception as e:
        if debug:
            print(f"      [decode] 暴力破解异常: {e}")
        return None


def decode_dat_file_fast(dat_path, output_path=None, debug=False):
    """快速解码 — 基于常见 XOR 密钥

    微信 3.x 版本常用 XOR 密钥:
    - 图片: 0x1F, 0xAB, 0xAC 等
    """
    if not os.path.exists(dat_path):
        if debug:
            print(f"      [decode] 文件不存在: {dat_path}")
        return None

    # 常见 XOR 密钥列表
    COMMON_KEYS = [0x1F, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xD5]

    try:
        with open(dat_path, 'rb') as f:
            data = f.read()

        if debug:
            print(f"      [decode] 文件大小: {len(data)} bytes")
            print(f"      [decode] 前10字节(hex): {data[:10].hex()}")

        if len(data) < 10:
            if debug:
                print(f"      [decode] 文件太小")
            return None

        for xor_key in COMMON_KEYS:
            decoded_header = bytes([b ^ xor_key for b in data[:3]])

            if decoded_header == JPG_HEADER:
                decoded_data = bytes([b ^ xor_key for b in data])

                if output_path is None:
                    output_path = str(dat_path).replace('.dat', '.jpg')

                with open(output_path, 'wb') as f:
                    f.write(decoded_data)

                if debug:
                    print(f"      [decode] 成功! XOR密钥=0x{xor_key:02X}")
                return output_path

        # 如果常见密钥都不行，用暴力破解
        if debug:
            print(f"      [decode] 常见密钥失败，尝试暴力破解...")
        return decode_dat_file(dat_path, output_path, debug=debug)

    except Exception as e:
        if debug:
            print(f"      [decode] 异常: {e}")
        return None


def batch_decode_images(dat_dir, output_dir):
    """批量解码目录下所有 .dat 文件

    Args:
        dat_dir: .dat 文件目录
        output_dir: 输出目录

    Returns:
        dict: {dat_name: decoded_path}
    """
    results = {}

    if not os.path.exists(dat_dir):
        return results

    os.makedirs(output_dir, exist_ok=True)

    for dat_file in Path(dat_dir).glob('*.dat'):
        if dat_file.name.endswith('_h.dat'):  # 缩略图，跳过
            continue

        output_path = os.path.join(output_dir, dat_file.name.replace('.dat', '.jpg'))
        decoded = decode_dat_file_fast(str(dat_file), output_path)

        if decoded:
            results[dat_file.name] = decoded

    return results