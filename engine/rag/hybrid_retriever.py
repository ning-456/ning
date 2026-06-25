"""混合检索模块 - 语义向量检索 + Cross-Encoder 重排序（可选）"""

from typing import Optional

import config


class HybridRetriever:
    """混合检索引擎：语义向量检索 + 可选 Cross-Encoder 重排序"""

    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base
        self._reranker = None
        self._reranker_loaded = False

    # ── 延迟加载 reranker（失败时不阻塞） ──────────────────
    def _get_reranker(self):
        if self._reranker_loaded:
            return self._reranker
        self._reranker_loaded = True  # 只尝试一次
        try:
            from sentence_transformers import CrossEncoder
            model_name = config.RERANK_MODEL
            print(f"[Reranker] 加载 Cross-Encoder: {model_name}")
            self._reranker = CrossEncoder(
                model_name,
                max_length=512,
                trust_remote_code=True,
            )
            print("[Reranker] 加载成功")
        except Exception as e:
            print(f"[Reranker] 加载失败（跳过重排序）: {e}")
            self._reranker = None
        return self._reranker

    # ── 单次检索 ──────────────────────────────────────────
    def search(self, query: str, top_k: Optional[int] = None) -> list[dict]:
        """语义向量检索 → 可选 Cross-Encoder 重排序"""
        if top_k is None:
            top_k = config.RETRIEVAL_TOP_K

        # 1. 向量检索（召回更多候选给 reranker）
        vector_k = max(top_k * 3, 15)
        candidates = self.knowledge_base.vector_search(query, top_k=vector_k)

        if not candidates:
            return []

        # 2. 尝试重排序
        reranker = self._get_reranker()
        if reranker is not None and len(candidates) > top_k:
            pairs = [[query, c["text"][:512]] for c in candidates]
            scores = reranker.predict(pairs, show_progress_bar=False)
            scored = list(zip(candidates, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            results = []
            for c, s in scored[:top_k]:
                c = dict(c)
                c["score"] = round(float(s), 6)
                results.append(c)
            return results

        # 3. 无 reranker 时直接截断
        return candidates[:top_k]

    # ── 多子问题检索（汇总结果）───────────────────────────
    def search_sub_questions(self, sub_questions: list[str]) -> dict:
        all_chunks_map: dict[str, dict] = {}
        all_image_ids: list[str] = []
        per_question: dict[str, dict] = {}

        for idx, sub_q in enumerate(sub_questions):
            key = f"q{idx + 1}"
            results = self.search(sub_q)

            if results:
                per_question[key] = {
                    "question": sub_q,
                    "chunks": results,
                    "image_ids": self._collect_image_ids(results),
                }

                for r in results:
                    cid = r.get("chunk_id", "")
                    if cid and cid not in all_chunks_map:
                        all_chunks_map[cid] = r
                        all_image_ids.extend(r.get("image_ids", []))

        seen: set[str] = set()
        unique_image_ids: list[str] = []
        for img_id in all_image_ids:
            if img_id not in seen:
                seen.add(img_id)
                unique_image_ids.append(img_id)

        return {
            "all_chunks": list(all_chunks_map.values()),
            "all_image_ids": unique_image_ids,
            "per_question": per_question,
        }

    @staticmethod
    def _collect_image_ids(results: list[dict]) -> list[str]:
        all_ids: list[str] = []
        for r in results:
            all_ids.extend(r.get("image_ids", []))
        seen: set[str] = set()
        unique: list[str] = []
        for img_id in all_ids:
            if img_id not in seen:
                seen.add(img_id)
                unique.append(img_id)
        return unique
