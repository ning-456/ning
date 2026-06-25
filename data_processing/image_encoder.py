"""
图片编码模块
将手册插图统一转换为Base64编码，建立图片索引
"""
import base64
import os
import json
from typing import Dict
from PIL import Image
import io


def get_image_mime_type(filepath: str) -> str:
    """根据文件扩展名获取MIME类型"""
    ext = os.path.splitext(filepath)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/jpeg")


def encode_image_to_base64(image_path: str, max_size_mb: int = 5) -> str:
    """
    将图片文件编码为Base64字符串，带data URI前缀

    Args:
        image_path: 图片文件路径
        max_size_mb: 最大允许大小(MB)，超过则压缩

    Returns:
        str: Base64编码字符串（含data:image/...;base64,前缀）
    """
    mime_type = get_image_mime_type(image_path)
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

    if file_size_mb > max_size_mb:
        # 压缩图片到max_size_mb以内
        img = Image.open(image_path)
        # 估算压缩比例
        scale = (max_size_mb / file_size_mb) ** 0.5
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

        buffer = io.BytesIO()
        format_name = img.format or "JPEG"
        if format_name == "PNG":
            img.save(buffer, format="PNG", optimize=True)
        else:
            img.save(buffer, format="JPEG", quality=85, optimize=True)
        img_bytes = buffer.getvalue()
    else:
        with open(image_path, "rb") as f:
            img_bytes = f.read()

    base64_str = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_str}"


def build_image_index(illustration_dir: str, output_path: str = None) -> Dict[str, str]:
    """
    扫描插图目录，建立图片ID到Base64编码的索引

    Args:
        illustration_dir: 插图目录路径
        output_path: 索引文件输出路径（可选）

    Returns:
        dict: {image_id: base64_string}
    """
    image_index = {}
    supported = {".png", ".jpg", ".jpeg", ".webp"}

    files = sorted(os.listdir(illustration_dir))
    total = len([f for f in files if os.path.splitext(f)[1].lower() in supported])
    count = 0

    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in supported:
            continue

        image_id = os.path.splitext(filename)[0]
        filepath = os.path.join(illustration_dir, filename)

        count += 1
        if count % 200 == 0:
            print(f"  编码进度: {count}/{total}")

        try:
            base64_str = encode_image_to_base64(filepath)
            image_index[image_id] = base64_str
        except Exception as e:
            print(f"  [!] 编码失败 {filename}: {e}")
            continue

    print(f"  图片编码完成: {len(image_index)}/{total}")

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(image_index, f, ensure_ascii=False, indent=2)
        print(f"  索引已保存: {output_path}")

    return image_index


def load_image_index(index_path: str) -> Dict[str, str]:
    """加载已保存的图片索引"""
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)
