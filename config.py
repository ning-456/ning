"""系统统一配置文件。所有模块从此文件读取配置，避免硬编码"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"
CHROMA_DB_PATH = os.path.join(os.environ.get("TEMP", str(KNOWLEDGE_BASE_DIR)), "dl_kb_chroma")
IMAGE_INDEX_PATH = str(KNOWLEDGE_BASE_DIR / "image_index.json")
TEXT_IMAGE_MAPPING_PATH = str(KNOWLEDGE_BASE_DIR / "text_image_mapping.json")
MANUAL_DIR = str(PROJECT_ROOT / "手册")
ILLUSTRATION_DIR = str(PROJECT_ROOT / "手册" / "插图")
QUESTION_CSV_PATH = str(PROJECT_ROOT / "data" / "question_public.csv")
SUBMISSION_CSV_PATH = str(PROJECT_ROOT / "data" / "submission_example.csv")

API_HOST = "0.0.0.0"
API_PORT = 8000
API_TOKEN = "sk_customer_20260304"
TEXT_TIMEOUT = 20
IMAGE_TIMEOUT = 30

LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")

VLM_API_KEY = os.getenv("VLM_API_KEY", LLM_API_KEY)
VLM_API_BASE = os.getenv("VLM_API_BASE", LLM_API_BASE)
VLM_MODEL = os.getenv("VLM_MODEL", "gpt-4o-mini")

# ========== 运行时热切换变量（通过 API 切换，不影响配置文件） ==========
CURRENT_LLM_MODEL = LLM_MODEL
CURRENT_VLM_MODEL = VLM_MODEL

VLM_MAX_TOKENS = 512
VLM_MODE = "api"  # VLM also uses Ollama API

# ========== Embedding 与重排序模型 ==========
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
EMBEDDING_DIM = 512
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# ========== 检索参数 ==========
VECTOR_SEARCH_TOP_K = 20       # 向量召回候选数（给reranker更多选择）
RETRIEVAL_TOP_K = 5            # 最终返回给下游的chunk数
LLM_MAX_CHUNKS = 5             # LLM 生成时最多使用多少个 chunk

# 英文 RAG 检索的 top-1 score 阈值，低于此值认为无相关内容
ENGLISH_RAG_THRESHOLD = float(os.getenv("ENGLISH_RAG_THRESHOLD", "0.01"))  # 低阈值因reranker对跨语言打分极低(0.01-0.05)

# ========== 文本分块参数 ==========
CHUNK_MIN_CHARS = 300
CHUNK_MAX_CHARS = 1000
CHUNK_OVERLAP_CHARS = 100

# ========== 对话管理 ==========
SESSION_TTL_SECONDS = 3600
MAX_HISTORY_ROUNDS = 5

# ========== 子问题检测模式 ==========
SUB_QUESTION_PATTERNS = [r"①", r"②", r"③", r"④", r"⑤"]

# ========== LLM 生成参数 ==========
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.5"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))

# ========== LLM开关 (Ollama API 模式，默认 http://localhost:11434/v1) ==========
USE_LLM = os.getenv("USE_LLM", "true").lower() == "true"
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
