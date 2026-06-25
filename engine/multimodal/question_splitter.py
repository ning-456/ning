"""多问题拆解模块"""

import re
from typing import Optional

import config


class QuestionSplitter:
    """用户问题拆解引擎。

    检测用户问题中是否包含多个子问题（通过问号、编号序号等模式），
    并将复合问题拆解为独立的子问题列表，便于逐项检索和回答。
    """

    def __init__(self):
        """初始化拆解模式列表。"""
        # 从 config 中加载子问题检测模式
        self._patterns = config.SUB_QUESTION_PATTERNS

        # 内置的完整模式列表
        self._split_patterns = [
            # 问号结尾的子句（中文问号 + 英文问号）
            (r"[^？?]+[？?]", "question_mark"),
            # 带编号的数字序号：1. xxx 2. xxx
            (r"(?:\d+[\.\、\s]\s*)[^。？?]+", "numbered"),
            # 带括号数字：(1) xxx (2) xxx
            (r"(?:[(（]\d+[)）]\s*)[^。？?]+", "parenthesized"),
            # 中文序号：第一/首先/其次/最后
            (r"(?:第一|第二|第三|第四|第五|首先|其次|再次|最后)[^，,。？?]+", "ordinal_cn"),
        ]

    def split(self, question: str) -> list[str]:
        """将复合问题拆解为独立的子问题列表。

        Args:
            question: 用户原始提问文本

        Returns:
            子问题字符串列表；如果只有一个问题则返回 [question]
        """
        if not self.is_multi_question(question):
            return [question.strip()]

        sub_questions = self._split_by_question_marks(question)
        if len(sub_questions) > 1:
            return [q.strip() for q in sub_questions if q.strip()]

        sub_questions = self._split_by_numbering(question)
        if len(sub_questions) > 1:
            return [self._clean_sub_question(q) for q in sub_questions if q.strip()]

        # 兜底：返回原问题
        return [question.strip()]

    def is_multi_question(self, question: str) -> bool:
        """判断用户问题是否包含多个子问题。

        Args:
            question: 用户提问文本

        Returns:
            True 表示包含多个子问题
        """
        # 检查是否包含多个问号
        q_marks = len(re.findall(r"[？?]", question))
        if q_marks > 1:
            return True

        # 检查编号模式
        numbered = re.findall(r"(?:\d+[\.\、\s])", question)
        if len(numbered) > 1:
            return True

        # 检查圆圈数字
        circled_count = 0
        for p in self._patterns:
            if re.search(p, question):
                circled_count += 1
        if circled_count > 1:
            return True

        # 检查中文序号
        cn_ordinal = re.findall(r"(?:第一|第二|第三|第四|第五|首先|其次|再次|最后)", question)
        if len(cn_ordinal) > 1:
            return True

        return False

    def _split_by_question_marks(self, text: str) -> list[str]:
        """按问号拆分子句，并保留问号。

        Args:
            text: 原始文本

        Returns:
            拆解后的子句列表
        """
        parts = re.split(r"([？?])", text)
        result = []
        buffer = ""
        for part in parts:
            buffer += part
            if part in ("？", "?"):
                result.append(buffer.strip())
                buffer = ""
        if buffer.strip():
            result.append(buffer.strip())
        return result

    def _split_by_numbering(self, text: str) -> list[str]:
        """按编号序号（1. 2. 第一 第二 等）拆解文本。

        Args:
            text: 原始文本

        Returns:
            拆解后的子句列表
        """
        # 先尝试按圆圈数字拆
        for pattern in self._patterns:
            if re.search(pattern, text):
                parts = re.split(f"({pattern})", text)
                # 合并标记和后续内容
                merged = []
                i = 0
                while i < len(parts):
                    if re.match(pattern, parts[i]):
                        merged.append(parts[i] + (parts[i + 1] if i + 1 < len(parts) else ""))
                        i += 2
                    else:
                        if parts[i].strip():
                            merged.append(parts[i])
                        i += 1
                return merged

        # 再尝试按数字编号拆
        parts = re.split(r"(\d+[\.\、]\s*)", text)
        merged = []
        i = 0
        while i < len(parts):
            if re.match(r"\d+[\.\、]\s*", parts[i]):
                merged.append(parts[i] + (parts[i + 1] if i + 1 < len(parts) else ""))
                i += 2
            else:
                if parts[i].strip():
                    merged.append(parts[i])
                i += 1
        return merged

    def _clean_sub_question(self, question: str) -> str:
        """清理子问题的编号前缀和多余空白。

        Args:
            question: 原始子问题

        Returns:
            清理后的子问题文本
        """
        q = question.strip()
        # 移除 "1." "1、" "(1)" "①" "第一" 等前缀
        q = re.sub(r"^\d+[\.\、\s]\s*", "", q)
        q = re.sub(r"^[(（]?\d+[)）]\s*", "", q)
        for p in self._patterns:
            q = re.sub(f"^{p}", "", q)
        q = re.sub(r"^(?:第一|第二|第三|第四|第五|首先|其次|再次|最后)[，,：:]?\s*", "", q)
        return q.strip()
