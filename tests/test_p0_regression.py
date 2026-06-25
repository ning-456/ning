"""P0 回归测试 — 确认 RAG 升级仍然正常工作"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from engine.rag.knowledge_base import KnowledgeBase
from engine.rag.hybrid_retriever import HybridRetriever

def test_knowledge_base():
    """1. 知识库能正常加载"""
    kb = KnowledgeBase()
    kb.load()
    assert len(kb.chunks) >= 150, f"chunks太少: {len(kb.chunks)}"
    assert kb.embeddings is not None, "embeddings未加载"
    print(f"  [OK] 知识库: {len(kb.chunks)} chunks, {kb.embeddings.shape[1]}维")
    return kb

def test_vector_search(kb):
    """2. 语义检索 top-1 正确"""
    results = kb.vector_search("如何使用VR头显的瞳距调节功能", top_k=3)
    assert results[0]["source"] == "VR头显手册", f"中文top-1错误: {results[0]['source']}"
    assert results[0]["score"] > 0.5, f"中文top-1 score太低: {results[0]['score']}"
    print(f"  [OK] 中文检索: top-1={results[0]['source']}, score={results[0]['score']:.4f}")

def test_english_search(kb):
    """3. 英文检索正确命中"""
    results = kb.vector_search("How to clean the air purifier filter", top_k=3)
    assert results[0]["source"] == "空气净化器手册", f"英文top-1错误: {results[0]['source']}"
    print(f"  [OK] 英文检索: top-1={results[0]['source']}, score={results[0]['score']:.4f}")

def test_reranker(kb):
    """4. Reranker 可加载并重排序"""
    hr = HybridRetriever(kb)
    results = hr.search("使用洗碗机前如何安装可折叠下层篮架", top_k=3)
    assert results[0]["source"] == "洗碗机手册", f"reranker top-1错误: {results[0]['source']}"
    print(f"  [OK] Reranker: top-1={results[0]['source']}, score={results[0]['score']:.4f}")

def test_no_hallucination(kb):
    """5. 无对应手册时返回低分"""
    results = kb.vector_search("What is the max load of the jetski?", top_k=3)
    # jetski 无对应手册，top-1 score 应较低
    assert results[0]["score"] < 0.5, f"无对应手册时score应低: {results[0]['score']}"
    print(f"  [OK] 无对应手册: top-1 score={results[0]['score']:.4f} < 0.5")

if __name__ == "__main__":
    print("P0 回归测试\n" + "=" * 40)
    kb = test_knowledge_base()
    test_vector_search(kb)
    test_english_search(kb)
    test_reranker(kb)
    test_no_hallucination(kb)
    print("=" * 40)
    print("全部通过! P0 状态正常")
