"""知识库管理模块 - 使用 sentence-transformers 语义向量检索 + 跨编码器重排序"""

import os
import pickle
import numpy as np

import config
from config import CHROMA_DB_PATH, TEXT_IMAGE_MAPPING_PATH, VECTOR_SEARCH_TOP_K


class KnowledgeBase:
    """多模态知识库：语义向量检索 + 图文联合检索"""

    def __init__(self, chroma_db_path: str = CHROMA_DB_PATH,
                 embedding_model_name: str = ""):
        self.db_path = chroma_db_path
        self.embedding_model_name = embedding_model_name or config.EMBEDDING_MODEL
        self._model = None
        self.embeddings = None
        self.chunks = []
        self.chunk_index = {}
        self.mapper = None

    # ── 延迟加载 embedding 模型 ────────────────────────────
    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"\n[KB] 加载 Embedding 模型: {self.embedding_model_name}")
            self._model = SentenceTransformer(
                self.embedding_model_name,
                trust_remote_code=True,
            )
            print(f"[KB] Embedding 维度: {self._model.get_embedding_dimension()}")
        return self._model

    # ── 构建索引 ──────────────────────────────────────────
    def build(self, chunks_with_images: list[dict]):
        """用 sentence-transformers 构建语义向量索引"""
        self.chunks = chunks_with_images
        for ch in self.chunks:
            self.chunk_index[ch["chunk_id"]] = ch

        texts = [ch["text"] for ch in self.chunks]
        model = self._get_model()

        print(f"  [KB] 编码 {len(texts)} 个 Chunk（batch_size=32）...")
        self.embeddings = model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True,
            batch_size=32,
        )

        os.makedirs(self.db_path, exist_ok=True)
        np.save(os.path.join(self.db_path, "embeddings.npy"), self.embeddings)
        with open(os.path.join(self.db_path, "chunks.pkl"), "wb") as f:
            pickle.dump(self.chunks, f)

        print(f"  [KB] 语义索引构建完成: {len(texts)} Chunks, {self.embeddings.shape[1]} 维")

    # ── 加载已构建的索引 ──────────────────────────────────
    def load(self):
        """从磁盘加载已构建的语义向量索引"""
        emb_path = os.path.join(self.db_path, "embeddings.npy")
        chunks_path = os.path.join(self.db_path, "chunks.pkl")

        if not os.path.exists(emb_path) or not os.path.exists(chunks_path):
            raise FileNotFoundError(
                f"知识库文件不存在（{emb_path}），请先运行 data_processing/build_knowledge_base.py"
            )

        self.embeddings = np.load(emb_path)
        with open(chunks_path, "rb") as f:
            self.chunks = pickle.load(f)

        for ch in self.chunks:
            self.chunk_index[ch["chunk_id"]] = ch

        # 延迟加载模型（查询时再加载）
        self._model = None

        from engine.rag.text_image_mapper import TextImageMapper
        self.mapper = TextImageMapper(TEXT_IMAGE_MAPPING_PATH)

        print(f"  知识库加载完成: {len(self.chunks)} Chunks, {self.embeddings.shape[1]} 维 Embedding")

    # ── 语义向量检索 ──────────────────────────────────────
    def vector_search(self, query: str, top_k: int = VECTOR_SEARCH_TOP_K) -> list[dict]:
        """用 sentence-transformers 做语义相似度搜索"""
        model = self._get_model()
        query_emb = model.encode([query], normalize_embeddings=True)
        # 点积 = cosine similarity（因已 L2 归一化）
        scores = np.dot(query_emb, self.embeddings.T)[0]

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "source": chunk["source"],
                "image_ids": chunk.get("image_ids", []),
                "score": round(float(scores[idx]), 6),
            })
        return results

    # ── 批量图片 ID 查询 ──────────────────────────────────
    def get_image_ids_for_chunks(self, chunk_ids: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for cid in chunk_ids:
            ch = self.chunk_index.get(cid)
            if ch:
                for img_id in ch.get("image_ids", []):
                    if img_id not in seen:
                        seen.add(img_id)
                        result.append(img_id)
        return result
