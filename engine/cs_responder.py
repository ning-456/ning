"""CS客服模板匹配模块 - 从cs_templates.json加载"""

import json
import os
import re

import config


class CSResponder:
    """客服模板匹配引擎"""

    # 否定词：如果问题包含这些词，不匹配对应类别的模板
    NEGATIVE_KEYWORDS = {
        "翻新机/假货": ["怎么用", "如何使用", "怎么操作", "步骤", "设置", "功能", "模式",
                       "如何", "怎么安装", "怎么拆", "怎么调", "如何设置"],
        "售后维修": ["怎么用", "如何使用", "操作步骤", "设置", "功能", "怎么安装"],
    }

    def __init__(self):
        self._templates = self._load_templates()

    def _load_templates(self):
        cs_path = os.path.join(config.KNOWLEDGE_BASE_DIR, "cs_templates.json")
        if os.path.exists(cs_path):
            try:
                with open(cs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates = []
                for item in data:
                    templates.append({
                        "category": item.get("category", ""),
                        "keywords": item.get("keywords", []),
                        "answer": item.get("answer", ""),
                        "min_match": item.get("min_match", 1),
                    })
                if templates:
                    return templates
            except Exception as e:
                print("[CSResponder] Failed to load cs_templates.json:", e)

        return [
            {"category": "物流", "keywords": ["物流", "快递", "发货"], "answer": "请提供订单号查询物流信息。", "min_match": 1},
            {"category": "售后", "keywords": ["售后", "维修", "保修"], "answer": "请描述故障情况，我们为您安排售后。", "min_match": 1},
        ]

    def match(self, question):
        if not question:
            return None

        import jieba
        question_tokens = set(jieba.lcut(question))
        question_lower = question.lower()

        best_match = None
        best_score = 0

        for template in self._templates:
            category = template.get("category", "")
            min_match = template.get("min_match", 1)
            matched_keywords = []

            for kw in template["keywords"]:
                kw_lower = kw.lower()
                kw_len = len(kw)

                matched = False
                if kw_len >= 4:
                    # 长关键词用子串匹配
                    if kw_lower in question_lower:
                        matched = True
                elif kw_len >= 2:
                    # 2-3字短关键词必须精确分词匹配（避免"颜色"匹配"颜色偏差"等误匹配）
                    if kw in question_tokens:
                        matched = True
                    # 放宽：如果关键词出现在问题中但没有被分词，也匹配
                    elif kw_lower in question_lower:
                        matched = True

                if matched:
                    matched_keywords.append(kw)

            # 检查 min_match 要求
            if len(matched_keywords) >= min_match:
                # 否定词检查
                negatives = self.NEGATIVE_KEYWORDS.get(category, [])
                has_negative = any(neg in question for neg in negatives)

                if not has_negative:
                    total_len = sum(len(kw) for kw in matched_keywords)
                    if total_len > best_score:
                        best_score = total_len
                        best_match = template["answer"]

        if best_match and best_score >= 2:
            return best_match

        return None
