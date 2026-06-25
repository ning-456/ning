"""答案后处理模块 - 修复版：保留原始 <PIC> 标签，正确输出图片ID"""

import re


class PostProcessor:
    """回答后处理引擎"""

    @staticmethod
    def process_answer(answer: str) -> str:
        """清理回答文本：去除多余空白"""
        if not answer:
            return ""
        result = re.sub(r"\n{3,}", "\n\n", answer)
        result = "\n".join(line.strip() for line in result.split("\n"))
        result = re.sub(r"[ \t]+", " ", result)
        result = result.strip()
        return result

    @staticmethod
    def deduplicate_image_ids(image_ids: list[str]) -> list[str]:
        """图片ID去重，保持顺序"""
        seen: set[str] = set()
        result: list[str] = []
        for img_id in image_ids:
            if img_id not in seen:
                seen.add(img_id)
                result.append(img_id)
        return result

    @staticmethod
    def format_final(answer: str, image_ids: list[str]) -> str:
        """格式化最终回答

        格式：保留原始 <PIC> 标签内联，不在末尾追加图片列表。
        API 输出格式由 answer 文本中的 <PIC> 标签承载。
        """
        if not answer:
            return ""

        # <PIC> 标签已内联在 answer 文本中，不额外追加
        return answer.strip()

    @staticmethod
    def polite_decline(question: str) -> str:
        return (
            "您好，我是产品使用咨询客服助手，专注于回答与产品使用、操作、"
            "功能、故障排除等相关的问题。您的问题似乎不在我的知识范围之内，"
            "请尝试提出与产品相关的问题，我会尽力为您解答。"
        )