"""
文本清洗与中文手册提取模块。

提供文本清理（去除空行、乱码字符、归一化空白）以及
从 JSON 格式的手册文件中提取并清洗文本内容的功能。
"""

import json
import os
import re
from typing import Union


def clean_text(text: str) -> str:
    """清理文本：去除空行、乱码字符、归一化空白。

    Args:
        text: 原始文本字符串。

    Returns:
        清洗后的文本。
    """
    if not isinstance(text, str):
        return ""

    # 去除零宽字符等不可见控制字符（保留换行和制表符）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 替换多种换行符为统一换行
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 去除行首行尾空白
    lines = [line.strip() for line in text.split('\n')]

    # 去除空行
    lines = [line for line in lines if line]

    # 合并行
    cleaned = '\n'.join(lines)

    # 将连续两个以上换行压缩为两个换行（段落分隔）
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    # 将多个连续空格、制表符合并为单个空格
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)

    # 修剪首尾空白
    cleaned = cleaned.strip()

    return cleaned


def _parse_manual_file(filepath: str):
    """读取并解析单个手册文件（JSON 格式）。

    手册文件内部存储为 JSON 数组：[text_content, [image_references]]

    Args:
        filepath: 手册文件完整路径。

    Returns:
        (text_content, image_references) 元组，解析失败返回 None。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) >= 1 and isinstance(data[0], str):
            text = data[0]
            images = data[1] if len(data) > 1 and isinstance(data[1], list) else []
            return text, images
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        pass
    return None


def extract_chinese_manuals(manual_dir: str) -> dict[str, str]:
    """读取 manual_dir 下所有中文手册（.txt 文件），提取并清洗文本。

    会跳过 "汇总英文手册.txt"。
    手册中的 `<PIC>` 标签会被保留以标记图片位置。

    Args:
        manual_dir: 手册所在目录路径。

    Returns:
        {文件名_stem: 清洗后的文本内容} 的字典。
    """
    manuals: dict[str, str] = {}
    if not os.path.isdir(manual_dir):
        return manuals

    for filename in sorted(os.listdir(manual_dir)):
        if not filename.endswith('.txt'):
            continue
        # 跳过英文手册
        if filename == '\u6c47\u603b\u82f1\u6587\u624b\u518c.txt':
            continue

        filepath = os.path.join(manual_dir, filename)
        parsed = _parse_manual_file(filepath)
        if parsed is None:
            continue

        text, _ = parsed
        cleaned = clean_text(text)
        stem = os.path.splitext(filename)[0]
        manuals[stem] = cleaned

    return manuals
