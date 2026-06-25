# 多模态客服智能体 — 开发约束规则

## 项目架构
- RAG: knowledge_base.py (sentence-transformers) → hybrid_retriever.py (Cross-Encoder reranker)
- Pipeline: pipeline.py (流程编排) → answer_assembler.py (LLM+规则) → post_processor.py (后处理)
- 对话管理: dialogue/manager.py (存储历史)
- 多模态: multimodal/ (VLM理解, 意图识别, 问题拆解)
- 外部LLM: Ollama API (qwen2.5:7b / qwen2.5:3b)

## 不可违反的规则（已完成的P0/P1）

### P0 — RAG检索（冻结）
1. `knowledge_base.py` 必须使用 `sentence-transformers` 语义向量检索，**不得回退到 TF-IDF / BM25 / RRF**
2. `hybrid_retriever.py` 搜索流程：向量检索(召回) → 可选 Cross-Encoder 重排序(精排)
3. `config.py` 关键参数：`VECTOR_SEARCH_TOP_K=20`, `RETRIEVAL_TOP_K=5`, `RERANK_MODEL=BAAI/bge-reranker-v2-m3`
4. 知识库路径：`$TEMP\dl_kb_chroma`（152 chunks, 512维, 20份手册）

### P1 — 幻觉抑制（冻结）
1. **pipeline.py 流程**：
   - step 5: RAG检索 → step 6: 英文低分阈值(0.01) + EN_PRODUCT_MAP二次定位
   - step 7: 按产品过滤chunk（英文用`_find_product_by_en_map`, 中文用`_find_chinese_product`）
   - step 8.1: 低分拦截（chunk为空或英文score<阈值时返回Sorry）
   - step 8.2: 产品名称验证（映射表+手册名扫描双保险）
   - step 8.3: LLM生成 → step 9-11后处理 → step 12: 事后幻觉检测(数字/型号验证)
2. **answer_assembler.py**：
   - 英文 grounding：提取术语验证（threshold=0.3）
   - 中文 grounding：threshold=0.25
   - `_grounding_light` 不通过则降级到 `_extract_and_polish`
3. **无对应产品时返回**：`Sorry, no relevant information found for this product.`

### P5 — 代码约束
1. 改动 RAG 检索时必须运行 `tests/test_p0_regression.py` 验证5项测试全部通过
2. 改动 LLM prompt 时必须测试中英文各至少3题
3. 改动 pipeline 时必须测试 CS模板 + 中文产品 + 英文产品 三类问题
4. 所有可调参数写在 `config.py`，禁止硬编码
5. 回答不得以 "Here is the relevant information"、"以下是相关信息"等前缀开头

## 英文产品映射表 (EN_PRODUCT_MAP)
位于 `engine/pipeline.py`，约 15 个产品类别的同义词→中文手册名映射。
当 RAG 检索分数低时用于二次定位。涵盖了常见英文产品关键词。

## P2 — 多轮对话利用（已完成）
1. `answer_assembler.assemble()` 新增 `dialogue_history` 参数，接收来自 DialogueManager 的历史
2. `_try_llm()` 在 system prompt 后注入最近 2 轮对话历史（<=4 条消息），帮助 LLM 理解指代
3. `pipeline.process()` 中新增 `enhanced_question` 机制：
   - 当前问题不含产品名时，从历史最近一轮用户提问中提取产品信息
   - 产品检测（step 6/7/8.2）使用 `enhanced_question` 而非原始 `question`
4. `manual_chunks` 兜底修复：为手工提取的 chunks 补充 `score=0.5` 默认值，避免被低分拦截
5. step 8.1 低分拦截前增加 `prev_product` 兜底检查

## 已知待完成任务
- P3: 多模态（手册插图2608张的描述生成 + 图文联合检索）
- P4: 模型微调（优先级最低）
