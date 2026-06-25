"""答案组装模块 - LLM + 规则润色双通道"""

from typing import Optional
import re
import config


class AnswerAssembler:
    """答案组装引擎：选择性调用 LLM 生成，规则提取做兜底润色"""

    def _is_english(self, text: str) -> bool:
        return bool(re.search(r"[a-zA-Z]{4,}", text)) and not bool(re.search(r"[\u4e00-\u9fff]", text))

    def _get_llm(self):
        from engine.generation.llm_client import LLMClient
        llm = LLMClient()
        return llm if llm.enabled else None

    def assemble(self, question, sub_questions, rag_context, image_chunks=None, dialogue_history=None):
        all_chunks = rag_context.get("all_chunks", [])

        if not all_chunks:
            return self._no_result_answer(question)

        needs_llm = self._should_use_llm(question, all_chunks, sub_questions)

        if needs_llm:
            llm = self._get_llm()
            if llm:
                result = self._try_llm(question, sub_questions, all_chunks, llm, dialogue_history)
                if result and self._is_valid_answer(result):
                    if self._grounding_light(result, all_chunks):
                        return result

        return self._extract_and_polish(question, all_chunks)

    def _should_use_llm(self, question, chunks, sub_questions):
        if self._is_english(question):
            return True
        if len(sub_questions) > 1:
            return True
        if len(chunks) <= 2 and sum(len(c.get("text", "")) for c in chunks) < 200:
            return False
        if any(w in question for w in ["如何", "怎么", "步骤", "设置", "调节", "区别", "对比"]):
            return True
        return sum(len(c.get("text", "")) for c in chunks[:3]) > 300

    def _try_llm(self, question, sub_questions, all_chunks, llm, dialogue_history=None):
        context_parts = []
        for i, c in enumerate(all_chunks[:config.LLM_MAX_CHUNKS]):
            source = c.get("source", "").replace("手册", "")
            text = c.get("text", "")
            if len(text) > 800:
                text = text[:800] + "..."
            context_parts.append(f"[来源：{source}]\n{text}")
        context_str = "\n\n---\n\n".join(context_parts)

        is_eng = self._is_english(question)

        if is_eng:
            messages = [{"role": "system", "content": self._english_system_prompt()}]
            if dialogue_history:
                for h in dialogue_history[-4:]:
                    messages.append(h)
            messages.append({"role": "user", "content": f"Manual content:\n{context_str}\n\nUser question: {question}\n\nAnswer:"})
        else:
            messages = [{"role": "system", "content": self._chinese_system_prompt()}]
            if dialogue_history:
                for h in dialogue_history[-4:]:
                    messages.append(h)
            messages.append({"role": "user", "content": f"手册内容：\n{context_str}\n\n用户问题：{question}\n\n回答："})

        raw = llm.generate(messages)
        if not raw:
            return None
        return raw.strip()

    def _chinese_system_prompt(self):
        return (
            "你是一个产品使用客服助手。下面是从产品手册中检索到的相关内容。\n\n"
            "要求：\n"
            "1. 直接给出答案，不要加「以下是相关信息」等前缀\n"
            "2. 语言自然流畅，像客服在说话\n"
            "3. 如果手册中提到相关图片，在合适位置标上 <PIC>\n"
            "4. 用户问了多个问题请逐条回答，用数字序号分隔\n"
            "5. 手册内容中没有的信息不要编造，不确定时说「建议查阅手册对应章节」\n"
            "6. 回答要具体，引用手册中的操作步骤、型号和参数\n"
            "7. 保持简洁，一般不超过 300 字\n8. 如果对话历史中有上一轮的问题和回答，注意结合上下文理解当前问题的指代（如「它」「这个」「那」等），避免重复回答已经说过的内容"
        )

    def _english_system_prompt(self):
        return (
            "You are a customer service agent for product manuals. Below is relevant content retrieved from Chinese product manuals.\n\n"
            "Requirements:\n"
            "1. Answer directly, no prefixes like 「Here is the relevant information」\n"
            "2. Use natural, fluent English\n"
            "3. Extract SPECIFIC steps, details, and numbers from the manual content\n"
            "4. If the manual mentions related images, insert <PIC> tags at appropriate positions\n"
            "5. If there are multiple sub-questions, answer each one separately with numbering\n"
            "6. Do NOT make up information not in the manual\n"
            "7. Be specific - cite actual manual content (model numbers, step numbers, measurements)\n"
            "8. Keep concise, under 300 words\n9. If there is conversation history, use it to resolve pronouns (it, this, that) and avoid repeating previously answered content"
        )

    def _is_valid_answer(self, answer):
        if not answer or len(answer) < 10:
            return False
        invalid_prefixes = ["用户问题", "用户：", "Question:", "用户提问"]
        for p in invalid_prefixes:
            if answer.startswith(p):
                return False
        if len(answer) > 1500:
            return False
        return True

    def _grounding_light(self, answer, chunks, threshold=0.25):
        import jieba
        # 英文 grounding：提取关键术语/数字验证
        if self._is_english(answer):
            terms = set()
            for m in re.finditer(r"(?:[A-Z0-9]{2,})|(?:\d+(?:\.\d+)?\s*(?:mm|cm|kg|lb|mph|kmh|hr|min|sec|V|W|A|[CF]))", answer):
                terms.add(m.group(0).lower())
            if not terms:
                return True  # 无可验证术语
            all_text = " ".join(c.get("text", "") for c in chunks).lower()
            found = sum(1 for t in terms if t in all_text)
            return found / len(terms) >= 0.3  # 至少 30% 术语匹配
        
        # 中文 grounding
        ans_words = set()
        for w in jieba.lcut(answer):
            if re.search(r"[\u4e00-\u9fff]", w) and len(w) >= 3:
                ans_words.add(w)
        for m in re.findall(r"[a-zA-Z]{3,}", answer):
            ans_words.add(m.lower())
        for m in re.findall(r"[A-Z0-9]{3,}", answer):
            ans_words.add(m)

        if not ans_words:
            return True

        all_text = " ".join(c.get("text", "") for c in chunks)
        all_text_lower = all_text.lower()
        found = sum(1 for w in ans_words if (isinstance(w, str) and w.lower() in all_text_lower) or w in all_text)
        ratio = found / len(ans_words) if ans_words else 1.0
        return ratio >= threshold

    def _extract_and_polish(self, question, all_chunks):
        import jieba
        is_eng = self._is_english(question)
        stop_words = set(["安全", "警告", "危险", "小心", "注意", "说明", "保存"])
        q_keywords = set(w for w in jieba.lcut(question) if len(w) >= 2 and w not in stop_words)
        if is_eng:
            q_keywords = set(w.lower() for w in re.findall(r"[a-zA-Z]{3,}", question))

        best_lines = []
        seen = set()
        for chunk in all_chunks[:5]:
            text = chunk.get("text", "")
            for line in text.split("\n"):
                line = line.strip()
                if not line or line in seen:
                    continue
                line_clean = re.sub(r"^#+\s*", "", line)
                if any(kw in line for kw in ["警告", "危险", "小心"]) and len(line) < 30:
                    continue
                if is_eng:
                    matched = any(kw in line.lower() for kw in q_keywords)
                else:
                    matched = any(kw in line for kw in q_keywords)
                if matched:
                    seen.add(line)
                    best_lines.append(line_clean)

        if best_lines:
            result = "\n".join(best_lines[:5])
            if len(result) > 500:
                result = result[:500] + "..."
            return result

        top = all_chunks[0].get("text", "")
        top = re.sub(r"^#+\s*", "", top.strip())
        return top[:300]

    @staticmethod
    def _no_result_answer(question):
        if re.search(r"[a-zA-Z]{4,}", question) and not re.search(r"[\u4e00-\u9fff]", question):
            return "Sorry, no relevant information found for this product."
        if re.search(r"[a-zA-Z]{5,}", question):
            return "Sorry, no relevant information found for this product."
        return "未找到相关信息，请尝试询问产品使用方面的问题。"
