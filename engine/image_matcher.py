"""图片匹配模块 - 通过图像获取相关文本块"""

class ImageMatcher:
    """图片匹配引擎。

    接收用户上传的图片（base64），通过VLM理解图片内容，
    然后与知识库中的文本块进行匹配，返回与图片相关的文本块。
    """

    def __init__(self):
        """初始化图片匹配器。"""
        self._vlm = None

    def _get_vlm(self):
        """延迟加载VLM图像理解模块。"""
        if self._vlm is None:
            from engine.multimodal.image_understanding import VLMImageUnderstanding
            self._vlm = VLMImageUnderstanding()
        return self._vlm

    def match(self, images: list[str]) -> list[dict]:
        """根据图片获取相关文本块。

        对每张图片进行VLM描述，返回包含图片描述和相关上下文的信息。

        Args:
            images: base64 编码的图片列表

        Returns:
            图片相关上下文列表，每项包含 image_index、description 等字段
        """
        if not images:
            return []

        vlm = self._get_vlm()
        results = []
        for i, img in enumerate(images):
            desc = vlm.describe_image(img)
            if desc:
                results.append({
                    "image_index": i,
                    "description": desc,
                })
        return results
