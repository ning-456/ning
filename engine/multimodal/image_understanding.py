"""VLM图像理解模块 - Plan B，支持本地VLM和API两种模式"""
import config


class VLMImageUnderstanding:
    """基于VLM的图像理解引擎，支持本地模型和OpenAI兼容API。"""

    def __init__(self):
        self.mode = "api"  # always API
        self.model_name = config.VLM_MODEL
        self.api_key = config.VLM_API_KEY
        self.api_base = config.VLM_API_BASE
        self.api_model = config.VLM_MODEL
        self.max_tokens = config.VLM_MAX_TOKENS
        self.client = None
        self.processor = None
        self.model = None

        if self.mode == "api" and self.api_key:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)

    def _load_local(self):
        if self.model is not None:
            return
        try:
            from transformers import AutoModelForVision2Seq, AutoProcessor
            print(f"[VLM] 加载本地VLM模型: {self.model_name} ...")
            self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
            self.model = AutoModelForVision2Seq.from_pretrained(self.model_name, trust_remote_code=True, device_map="auto")
            print(f"[VLM] 本地VLM模型加载完成")
        except Exception as e:
            print(f"[VLM] 本地VLM加载失败: {e}")
            self.model = "mock"

    def describe_image(self, bs):
        """描述单张图片，bs为Base64字符串"""
        if not bs:
            return ""
        if self.mode == "api":
            return self._desc_api(bs)
        return self._desc_local(bs)

    def _desc_api(self, bs):
        if not self.client:
            return ""
        try:
            r = self.client.chat.completions.create(
                model=self.api_model,
                messages=[{"role":"user","content":[{"type":"text","text":"请详细描述这张图片中的内容和其主要用途，包括任何可见的文字、图标、产品部件等。"},{"type":"image_url","image_url":{"url":bs}}]}],
                max_tokens=self.max_tokens)
            return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"[VLM] API描述失败: {e}")
            return ""

    def _desc_local(self, bs):
        self._load_local()
        if self.model == "mock":
            return ""
        try:
            import base64
            from PIL import Image
            import io
            if "," in bs:
                bs = bs.split(",", 1)[1]
            img = Image.open(io.BytesIO(base64.b64decode(bs)))
            msgs = [{"role":"user","content":[{"type":"image","image":img},{"type":"text","text":"请详细描述这张图片中的内容和其主要用途。"}]}]
            prompt = self.processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = self.processor(text=prompt, images=img, return_tensors="pt").to(self.model.device)
            out = self.model.generate(**inputs, max_new_tokens=self.max_tokens)
            return self.processor.decode(out[0], skip_special_tokens=True).strip()
        except Exception as e:
            print(f"[VLM] 本地描述失败: {e}")
            return ""

    def describe_images(self, images):
        """批量描述多张图片"""
        descs = []
        for i, img in enumerate(images):
            d = self.describe_image(img)
            if d:
                descs.append(f"[图片{i+1}]: {d}")
        return "\n".join(descs)
