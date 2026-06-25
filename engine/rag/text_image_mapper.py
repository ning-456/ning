"""文本-图片映射查找模块"""

import json
import os
from typing import Optional

import config


class TextImageMapper:
    """文本-图片映射查找引擎。

    加载 text_image_mapping.json 文件，提供按 chunk_id 查询关联图片 ID 的功能，
    支持单个查询和批量聚合查���。
    """

    def __init__(self, mapping_path: Optional[str] = None):
        """加载文本-图片映射文件。

        Args:
            mapping_path: text_image_mapping.json 的路径，默认使用 config
        """
        self.mapping_path = mapping_path or config.TEXT_IMAGE_MAPPING_PATH
        self._mapping: dict[str, list[str]] = {}
        self._load()

    def _load(self):
        """从 JSON 文件加载映射数据。"""
        if not os.path.exists(self.mapping_path):
            print(f"[TextImageMapper] Mapping file not found: {self.mapping_path}")
            self._mapping = {}
            return

        try:
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 支持两种格式：dict(chunk_id->image_ids) 或 list[{chunk_id,image_ids}]
            if isinstance(data, list):
                self._mapping = {item["chunk_id"]: item.get("image_ids", []) for item in data}
            else:
                self._mapping = data
            print(f"[TextImageMapper] Loaded {len(self._mapping)} chunk-image mappings.")
        except Exception as e:
            print(f"[TextImageMapper] Failed to load mapping: {e}")
            self._mapping = {}

    def get_image_ids(self, chunk_id: str) -> list[str]:
        """获取指定文本块关联的图片 ID。

        Args:
            chunk_id: 文本块唯一标识

        Returns:
            关联的图片 ID 列表；无关联时返回空列表
        """
        return self._mapping.get(chunk_id, [])

    def get_all_image_ids(self, chunk_ids: list[str]) -> list[str]:
        """聚合多个文本块的图片 ID，并去重。

        Args:
            chunk_ids: 文本块 ID 列表

        Returns:
            去重后的图片 ID 列表（保持出现顺序）
        """
        all_ids: list[str] = []
        for cid in chunk_ids:
            ids = self.get_image_ids(cid)
            all_ids.extend(ids)
        # 去重保持顺序
        seen: set[str] = set()
        unique: list[str] = []
        for img_id in all_ids:
            if img_id not in seen:
                seen.add(img_id)
                unique.append(img_id)
        return unique
