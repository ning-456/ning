"""管道编排器 - 客服智能体核心流程编排"""

from typing import Optional
import re

import config
from engine.multimodal.question_splitter import QuestionSplitter
from engine.multimodal.intent_recognizer import IntentRecognizer
from engine.rag.hybrid_retriever import HybridRetriever
from engine.rag.knowledge_base import KnowledgeBase
from engine.rag.text_image_mapper import TextImageMapper
from engine.dialogue.manager import DialogueManager
from engine.cs_responder import CSResponder
from engine.image_matcher import ImageMatcher
from engine.generation.answer_assembler import AnswerAssembler
from engine.generation.post_processor import PostProcessor


# ========== 英文产品到中文手册的同义词映射表 ==========
# 用于 RAG 分数低时的二次定位
EN_PRODUCT_MAP = {
    # VR头显
    "vr": "VR头显手册", "headset": "VR头显手册", "virtual reality": "VR头显手册",
    "h m d": "VR头显手册", "vr goggles": "VR头显手册", "head mounted": "VR头显手册",
    # 人体工学椅
    "ergonomic chair": "人体工学椅手册", "office chair": "人体工学椅手册",
    "seat": "人体工学椅手册", "mesh chair": "人体工学椅手册",
    # 健身单车
    "exercise bike": "健身单车手册", "stationary bike": "健身单车手册",
    "spin bike": "健身单车手册", "fitness bike": "健身单车手册", "cycling": "健身单车手册",
    # 健身追踪器
    "fitness tracker": "健身追踪器手册", "activity tracker": "健身追踪器手册", "trip screen": "健身追踪器手册", "display": "健身追踪器手册", "workout": "健身追踪器手册",
    "smart band": "健身追踪器手册", "smartwatch": "健身追踪器手册",
    "wristband": "健身追踪器手册", "fitness band": "健身追踪器手册",
    "tracker": "健身追踪器手册", "wearable": "健身追踪器手册",
    "watch": "健身追踪器手册", "band": "健身追踪器手册",
    # 儿童电动摩托车
    "children motorcycle": "儿童电动摩托车手册", "kid electric": "儿童电动摩托车手册",
    "electric motorcycle": "儿童电动摩托车手册", "ride on": "儿童电动摩托车手册",
    # 冰箱
    "refrigerator": "冰箱手册", "fridge": "冰箱手册", "freezer": "冰箱手册",
    "icebox": "冰箱手册", "refrigeration": "冰箱手册",
    # 功能键盘
    "keyboard": "功能键盘手册", "mechanical keyboard": "功能键盘手册",
    "gaming keyboard": "功能键盘手册", "keypad": "功能键盘手册",
    # 发电机
    "generator": "发电机手册", "power generator": "发电机手册",
    "portable generator": "发电机手册", "inverter": "发电机手册",
    # 温控器
    "thermostat": "可编程温控器手册", "temperature controller": "可编程温控器手册",
    "temperature control": "可编程温控器手册", "heating control": "可编程温控器手册",
    # 吹风机
    "hair dryer": "吹风机手册", "hairdryer": "吹风机手册", "blow dryer": "吹风机手册",
    "hair styling": "吹风机手册",
    # 摩托艇
    "motorboat": "摩托艇手册", "boat": "摩托艇手册", "engine oil": "摩托艇手册", "ship": "摩托艇手册",
    "watercraft": "摩托艇手册", "vessel": "摩托艇手册", "marine": "摩托艇手册",
    "speedboat": "摩托艇手册", "sailing": "摩托艇手册",
    "steer": "摩托艇手册", "rudder": "摩托艇手册",
    "navigation": "摩托艇手册", "sailing": "摩托艇手册", "anchor": "摩托艇手册",
    # 水泵
    "water pump": "水泵手册", "pump": "水泵手册", "bilge pump": "水泵手册",
    "submersible pump": "水泵手册", "utility pump": "水泵手册",
    # 洗碗机
    "dishwasher": "洗碗机手册", "dish washer": "洗碗机手册",
    # 烤箱
    "oven": "烤箱手册", "toaster": "烤箱手册", "grill": "烤箱手册",
    "air fryer": "烤箱手册", "airfryer": "烤箱手册", "convection oven": "烤箱手册",
    "toaster oven": "烤箱手册", "roast": "烤箱手册", "bake": "烤箱手册",
    # 电钻
    "drill": "电钻手册", "power drill": "电钻手册", "battery": "电钻手册", "dcb107": "电钻手册", "dcb112": "电钻手册", "electric drill": "电钻手册",
    "cordless drill": "电钻手册", "screwdriver": "电钻手册", "impact driver": "电钻手册",
    "hammer drill": "电钻手册", "dcb": "电钻手册",
    # 相机
    "camera": "相机手册", "digital camera": "相机手册", "af mode": "相机手册", "auto focus": "相机手册", "photograph": "相机手册", "dslr": "相机手册",
    "mirrorless": "相机手册", "photography": "相机手册", "lens": "相机手册",
    "shutter": "相机手册", "exposure": "相机手册", "photograph": "相机手册",
    # 空气净化器
    "air purifier": "空气净化器手册", "purifier": "空气净化器手册",
    "air cleaner": "空气净化器手册", "air filter": "空气净化器手册",
    # 空调
    "air conditioner": "空调手册", "a c": "空调手册", "air conditioning": "空调手册",
    "cooler": "空调手册", "heat pump": "空调手册", "climate control": "空调手册",
    # 蒸汽清洁机
    "steam cleaner": "蒸汽清洁机手册", "steam mop": "蒸汽清洁机手册",
    "steam cleaning": "蒸汽清洁机手册", "vapor cleaner": "蒸汽清洁机手册",
    # 蓝牙激光鼠标
    "bluetooth mouse": "蓝牙激光鼠标手册", "wireless mouse": "蓝牙激光鼠标手册",
    "laser mouse": "蓝牙激光鼠标手册", "optical mouse": "蓝牙激光鼠标手册",
}


class CustomerServicePipeline:
    """客服智能体核心管道"""

    def __init__(self):
        self.knowledge_base = KnowledgeBase()
        self.hybrid_retriever = HybridRetriever(self.knowledge_base)
        self.text_image_mapper = TextImageMapper()
        self.dialogue_manager = DialogueManager()
        self.intent_recognizer = IntentRecognizer()
        self.cs_responder = CSResponder()
        self.question_splitter = QuestionSplitter()
        self.answer_assembler = AnswerAssembler()
        self.post_processor = PostProcessor()
        self.image_matcher = ImageMatcher()
        self._kb_loaded = False

    def load_knowledge_base(self):
        if self._kb_loaded:
            return
        self._kb_loaded = True

        print("[Pipeline] Loading knowledge base...")
        self.knowledge_base.load()
        print(f"[Pipeline] Loaded {len(self.knowledge_base.chunks)} chunks")

        # RAG 检索改为语义向量 + Cross-Encoder 重排序

        # 加载图文映射
        self.text_image_mapper._load()

        # 收集所有手册 source 名
        all_sources = set()
        for c in self.knowledge_base.chunks:
            all_sources.add(c.get("source", ""))
        self._all_manual_names = all_sources
        print(f"[Pipeline] Manual sources: {len(all_sources)}")

    def _is_pure_english(self, question: str) -> bool:
        return bool(re.search(r"[a-zA-Z]{4,}", question)) and not bool(re.search(r"[\一-\鿿]", question))

    def _find_product_by_en_map(self, question: str) -> Optional[str]:
        q_lower = question.lower()
        matches = []
        for keyword, manual in EN_PRODUCT_MAP.items():
            if keyword in q_lower:
                matches.append((len(keyword), keyword, manual))
        if matches:
            matches.sort(key=lambda x: -x[0])
            return matches[0][2]
        return None

    def _get_rag_top_score(self, rag_context: dict) -> float:
        chunks = rag_context.get("all_chunks", [])
        if chunks:
            return chunks[0].get("score", 0.0)
        return 0.0

    def _find_chinese_product(self, question: str) -> Optional[str]:
        import jieba
        tokens = jieba.lcut(question)
        product_names = {
            "VR头显": "VR头显手册", "人体工学椅": "人体工学椅手册",
            "健身单车": "健身单车手册", "健身追踪器": "健身追踪器手册",
            "儿童电动摩托车": "儿童电动摩托车手册", "冰箱": "冰箱手册",
            "功能键盘": "功能键盘手册", "发电机": "发电机手册",
            "温控器": "可编程温控器手册", "吹风机": "吹风机手册",
            "摩托艇": "摩托艇手册", "水泵": "水泵手册", "洗碗机": "洗碗机手册",
            "烤箱": "烤箱手册", "电钻": "电钻手册", "相机": "相机手册",
            "空气净化器": "空气净化器手册", "空调": "空调手册",
            "蒸汽清洁机": "蒸汽清洁机手册", "鼠标": "蓝牙激光鼠标手册",
            "键盘": "功能键盘手册",
        }
        for token in tokens:
            if token in product_names:
                return product_names[token]
        return None

    def _no_result(self, question, session_id):
        if self._is_pure_english(question):
            answer = "Sorry, no relevant information found for this product."
        else:
            answer = "未找到相关信息，请尝试询问产品使用方面的问题。"
        self.dialogue_manager.add_turn(session_id, question, answer)
        return answer, session_id


    def process(self, question: str, images: Optional[list[str]] = None,
                session_id: Optional[str] = None) -> tuple[str, str]:
        if images is None:
            images = []
        session_id = self.dialogue_manager.get_or_create_session(session_id)

        # 多轮对话：当前问题无法识别产品时，从历史最近一轮的提问中提取产品信息
        dialogue_history = self.dialogue_manager.get_history(session_id)
        enhanced_question = question  # 默认与原始问题相同
        prev_product = None
        if dialogue_history:
            # 遍历所有历史用户提问，找到最近一条含产品名的
            found_product_q = None
            for h in reversed(dialogue_history):
                if h["role"] != "user":
                    continue
                if self._is_pure_english(h["content"]):
                    prod = self._find_product_by_en_map(h["content"])
                else:
                    prod = self._find_chinese_product(h["content"])
                if prod:
                    prev_product = prod
                    found_product_q = h["content"]
                    break  # 找到最近的含产品名的问题

            if found_product_q is not None:
                # 检查当前问题是否本身就有产品名
                has_product = False
                if self._is_pure_english(question):
                    has_product = bool(self._find_product_by_en_map(question))
                else:
                    has_product = bool(self._find_chinese_product(question))

                if not has_product:
                    enhanced_question = f"{question} [{found_product_q}]" if self._is_pure_english(question) else f"{question}（{found_product_q}）"
                # 即使当前问题有产品名，prev_product 也保留，供 step 6/8.1 兜底使用

        # 1. 意图过滤
        if not self.intent_recognizer.is_related_to_products(question):
            answer = self.post_processor.polite_decline(question)
            self.dialogue_manager.add_turn(session_id, question, answer)
            return answer, session_id

        # 2. CS 模板匹配
        cs_answer = self.cs_responder.match(question)
        if cs_answer:
            self.dialogue_manager.add_turn(session_id, question, cs_answer)
            return cs_answer, session_id

        # 3. 图片匹配（用户上传的图片）
        image_chunks = [] if not images else self.image_matcher.match(images)

        # 4. 拆解子问题
        sub_questions = self.question_splitter.split(question)

        # 5. RAG 全库检索
        rag_context = self.hybrid_retriever.search_sub_questions(sub_questions)

        is_eng = self._is_pure_english(question)

        # 6. 英文问题处理
        if is_eng:
            top_score = self._get_rag_top_score(rag_context)
            if top_score < config.ENGLISH_RAG_THRESHOLD:
                # RAG 分数低 → 查同义词映射表做二次定位
                product_source = self._find_product_by_en_map(enhanced_question)
                if product_source and product_source in self._all_manual_names:
                    # 重新检索
                    fallback_ctx = self.hybrid_retriever.search_sub_questions(sub_questions)
                    if fallback_ctx.get("all_chunks"):
                        rag_context = fallback_ctx
                    else:
                        manual_chunks = [c for c in self.knowledge_base.chunks
                                         if c.get("source", "") == product_source]
                        if manual_chunks:
                            rag_context["all_chunks"] = manual_chunks[:config.LLM_MAX_CHUNKS]
                            rag_context["all_image_ids"] = []
                            for c in rag_context["all_chunks"]:
                                rag_context["all_image_ids"].extend(c.get("image_ids", []))
                        else:
                            return self._no_result(question, session_id)
                else:
                    return self._no_result(question, session_id)

        # 7. 按产品过滤 chunk（中英文都做，英文用 EN_PRODUCT_MAP 找产品）
        if is_eng:
            product_source = self._find_product_by_en_map(enhanced_question)
        else:
            product_source = self._find_chinese_product(enhanced_question)
        if product_source:
            filtered = [c for c in rag_context.get("all_chunks", [])
                        if c.get("source", "") == product_source]
            if filtered:
                rag_context["all_chunks"] = filtered
            elif prev_product:
                # 过滤结果为空但已从历史识别到产品 → 强制取该手册的全部 chunks
                manual_chunks = []
                for c in self.knowledge_base.chunks:
                    if c.get("source", "") == prev_product:
                        mc = dict(c)
                        mc["score"] = 0.5
                        manual_chunks.append(mc)
                if manual_chunks:
                    rag_context["all_chunks"] = manual_chunks[:config.LLM_MAX_CHUNKS]

        # 8.1 低分拦截：无相关chunk或分数极低时直接返回Sorry
        all_chunks = rag_context.get("all_chunks", [])
        if not all_chunks:
            return self._no_result(question, session_id)
        if is_eng:
            top_score = self._get_rag_top_score(rag_context)
            if top_score < config.ENGLISH_RAG_THRESHOLD:
                # 分数低时尝试用历史产品信息兜底（先复查）
                if prev_product:
                    manual_chunks = []
                    for c in self.knowledge_base.chunks:
                        if c.get("source", "") == prev_product:
                            mc = dict(c)
                            mc["score"] = 0.5
                            manual_chunks.append(mc)
                    if manual_chunks:
                        rag_context["all_chunks"] = manual_chunks[:config.LLM_MAX_CHUNKS]
                    else:
                        return self._no_result(question, session_id)
                else:
                    return self._no_result(question, session_id)

        # 8.2 产品验证：用EN_PRODUCT_MAP查找产品，找不到时扫描手册名
        if is_eng:
            eng_product = self._find_product_by_en_map(enhanced_question)
            if eng_product:
                # 映射在手表中，检查是否存在
                if eng_product not in self._all_manual_names:
                    return self._no_result(question, session_id)
            else:
                # EN_PRODUCT_MAP未覆盖→扫描所有手册名，看问题中是否提到任何产品
                q_lower = question.lower()
                found_product = False
                for manual_name in self._all_manual_names:
                    manual_keywords = manual_name.replace("手册", "").strip()
                    if len(manual_keywords) >= 2 and manual_keywords.lower() in q_lower:
                        found_product = True
                        break
                if not found_product:
                    return self._no_result(question, session_id)

        # 8.3 生成回答
        raw_answer = self.answer_assembler.assemble(
            question=question, sub_questions=sub_questions,
            rag_context=rag_context, image_chunks=image_chunks,
            dialogue_history=dialogue_history,
        )

        # 9. 后处理
        cleaned_answer = self.post_processor.process_answer(raw_answer)

        # 10. 收集图片 ID
        all_image_ids = []
        for c in rag_context.get("all_chunks", []):
            all_image_ids.extend(c.get("image_ids", []))
        deduped_ids = self.post_processor.deduplicate_image_ids(all_image_ids)

        # 11. 清理 Markdown 前缀
        cleaned_answer = re.sub(r"^[#]+\s*", "", cleaned_answer.strip())
        cleaned_answer = re.sub(r'\n[#]+\s*', chr(10), cleaned_answer)

        final_answer = self.post_processor.format_final(cleaned_answer, deduped_ids)

        # 12. 幻觉检测：验证LLM回答中的关键事实是否在chunk中存在
        if is_eng and len(final_answer) > 20:
            import re as _re
            answer_terms = set()
            for _m in _re.finditer(r"(?:[A-Z0-9]{2,})|(?:\d+(?:\.\d+)?\s*(?:mm|cm|kg|lb|mph|kmh|hr|min|sec))", final_answer):
                answer_terms.add(_m.group(0).lower())
            if answer_terms:
                chunk_text = " ".join(c.get("text", "") for c in all_chunks).lower()
                found = sum(1 for t in answer_terms if t in chunk_text)
                if found / len(answer_terms) < 0.3:
                    final_answer = "Sorry, no relevant information found for this product."
            chinese_chars = len([c for c in final_answer if 0x4e00 <= ord(c) <= 0x9fff])
            if chinese_chars / max(len(final_answer), 1) > 0.8:

                final_answer = "Sorry, no relevant information found for this product."

        self.dialogue_manager.add_turn(session_id, question, final_answer)
        self.dialogue_manager.cleanup_expired()
        return final_answer, session_id


