# 项目决策记录（上下文压缩后参考）

## 已确认的决策

### 技术选型
- LLM: Ollama API (qwen2.5:7b 为主, qwen2.5:3b 用于快速测试)
- 嵌入模型: BAAI/bge-small-zh-v1.5（33MB, 已缓存）
- 重排序: BAAI/bge-reranker-v2-m3（2.2GB, 已下载缓存于 HF_HUB_OFFLINE）
- RAG: 语义向量检索 + Cross-Encoder 重排序, 不用 TF-IDF/BM25/RRF
- 手册: 20份中文手册, 152 chunks, 2608张插图

### 回答规范
- 不虚构、不超出检索范围, 但语言要重组改写使通畅
- 英文无对应手册时返回 "Sorry, no relevant information found for this product."
- 回答不以 "Here is the relevant information" 等前缀开头
- CS模板匹配优先级高于 LLM生成

### 英文产品映射
- EN_PRODUCT_MAP 存于 pipeline.py, 约15个产品类别
- "airfryer/air fryer" → 烤箱手册（合理映射, 保留）
- 不在映射表中的英文产品→扫描手册名→都不匹配则返回 Sorry

### 幻觉抑制方案
- 事前: 低分拦截（threshold+产品验证）
- 事中: LLM prompt强调"仅基于手册内容"
- 事后: grounding验证(数字/型号必须在chunk中出现)

### LLM 模式统一为 Ollama API（2026-06-21）
- 移除 `LLM_MODE`/`VLM_MODE` 本地 Transformers 模式，仅保留 Ollama API
- `config.py` 默认值改为：`LLM_API_BASE=http://localhost:11434/v1`, `LLM_API_KEY=ollama`, `LLM_MODEL=qwen2.5:7b`
- `llm_client.py` 精简为仅 API 模式，移除 `_load_local`/`_generate_local`
- `generate_submission.py` 不再需要设置 `LLM_MODE=api`，去掉 `ENGLISH_RAG_THRESHOLD` 覆盖
- 所有测试脚本统一从 `generate_submission.py` 复制环境变量

### P2 — 多轮对话利用（2026-06-21）
- `enhanced_question` 机制：当前问题无产品名时从历史中补全
- 产品检测步骤（step 6/7/8.2）使用 `enhanced_question`
- `manual_chunks` 补充 score=0.5 避免被低分拦截
- LLM prompt 注入最近 2 轮对话历史
- 修复 step 8.1 低分时的 prev_product 兜底检查
- 修复 `re.sub` escape sequence warning

### 当前得分
- submission1.csv: 0.08/1.0
- 改进目标: 0.5+

### 测试题
- 19题测试（已跑）: Q1,Q7,Q18,Q33,Q55,Q100,Q200,Q241,Q250,Q260,Q280,Q290,Q310,Q330,Q350,Q380,Q400,Q420,Q436
- 10题测试（已跑）: Q1,Q7,Q55,Q100,Q241,Q260,Q280,Q350,Q420,Q436
