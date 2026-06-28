"""LLM客户端封装 - 仅 Ollama API 模式。"""
from openai import OpenAI
import config


class LLMClient:
    """轻量LLM客户端，仅支持 Ollama API 模式。"""

    def __init__(self):
        self.enabled = config.USE_LLM
        self.api_client = None

        if self.enabled and bool(config.LLM_API_KEY):
            try:
                self.api_client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_API_BASE)
                print(f"[LLM] Ollama API 已连接: {config.LLM_API_BASE} (model={config.CURRENT_LLM_MODEL})")
            except Exception as e:
                print(f"[LLM] API连接失败: {e}")
                self.enabled = False
        else:
            self.enabled = False

    def generate(self, messages):
        if not self.enabled or self.api_client is None:
            return None
        try:
            r = self.api_client.chat.completions.create(
                model=config.CURRENT_LLM_MODEL, messages=messages,
                temperature=config.LLM_TEMPERATURE, max_tokens=config.LLM_MAX_TOKENS)
            return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM] API调用失败: {e}")
            return None
