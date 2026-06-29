# 多模态客服智能体 (Multimodal Customer Service Agent)

基于 **检索增强生成（RAG）** 与 **多模态大语言模型** 的智能客服系统，支持图文混合问答、多轮对话、意图识别与知识库检索。

本项目完整实现了 **多模态感知 + RAG知识检索 + 多轮对话管理 + 幻觉抑制** 四大核心模块的全链路客服智能体。

---

## 项目亮点

| 维度 | 核心设计 | 量化成果 |
|------|----------|----------|
| **RAG检索** | sentence-transformers 语义向量检索 + Cross-Encoder 重排序精排 | 152条知识切片，检索精准度大幅提升 |
| **幻觉抑制** | 6层防线：检索过滤->产品验证->Prompt约束->Grounding验证->事后检测->降级兜底 | 幻觉率从 32% 降至 6% |
| **多轮对话** | 历史2轮注入 + 产品名继承 + TTL过期管理 | 指代消解准确，复合问题拆分应答 |
| **多模态** | VLM图像理解 + 图文映射引擎（chunk->image_id） | 109条切片关联817张插图 |
| **数据迭代** | 7轮A榜评测->复盘->优化闭环 | 平均评分从 2.1 提升至 4.4 |

---

## 项目架构

### 四层架构

| 层级 | 职责 | 核心组件 |
|------|------|----------|
| **API层** | HTTP接口 & 身份认证 | FastAPI, Pydantic模型, Token鉴权 |
| **引擎层** | 核心业务逻辑编排 | PipeLine(12步), 对话管理, 意图识别, RAG检索, 答案生成 |
| **数据处理层** | 知识库预处理 | 文本清洗, 分块, Base64编码, 向量索引构建 |
| **基础设施层** | 存储与外部服务 | ChromaDB(语义索引), Ollama, Embedding模型 |

### 五大模块

| 模块 | 路径 | 功能 |
|------|------|------|
| **RAG检索** | engine/rag/ | sentence-transformers 语义向量检索 + Cross-Encoder 重排序 |
| **对话管理** | engine/dialogue/ | 多轮会话管理(TTL过期), 意图识别, 问题拆解 |
| **答案生成** | engine/generation/ | LLM生成(双通道) + 规则润色兜底 + 事后幻觉检测 |
| **多模态** | engine/multimodal/ | VLM图像理解, 用户意图识别, 多问题拆解 |
| **数据处理** | data_processing/ | 文本清洗/分块, Base64图片编码, 知识库构建 |


## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.10+ |
| pip | 21.0+ |
| Ollama (可选) | 本地部署 qwen2.5:7b |

### 安装依赖

`ash
pip install -r requirements.txt
`

首次运行会自动下载 Embedding 模型 (BAAI/bge-small-zh-v1.5 ~33MB)，确保网络通畅。

---

## 快速开始

### 1. 构建知识库

`ash
python data_processing/build_knowledge_base.py
`

构建完成后在 knowledge_base/ 和 %TEMP%\dl_kb_chroma 下生成：
- 向量索引 (embeddings.npy + chunks.pkl)
- 图片 Base64 索引 (image_index.json, 2608张)
- 图文映射 (	ext_image_mapping.json)
- 客服模板 (cs_templates.json)

### 2. 配置 LLM (可选)

通过环境变量或修改 config.py:

`ash
set USE_LLM=true
set LLM_API_BASE=http://localhost:11434/v1
set LLM_MODEL=qwen2.5:7b
`

系统默认不依赖 LLM，纯规则模式也可运行。

### 3. 启动服务

`ash
python main.py
`

服务监听 http://0.0.0.0:8000

### 4. 测试服务

`ash
# 健康检查
curl http://localhost:8000/health

# 客服咨询
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer sk_customer_20260304" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"VR头显如何调节瞳距？\"}"
`

---

## API 文档

### 健康检查

`
GET /health
`

**响应示例**
`json
{ "status": "ok", "timestamp": 1712345678, "active_sessions": 0, "kb_loaded": true }
`

### 客服咨询

`
POST /chat
`

#### 请求头
| 字段 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token, Bearer sk_customer_20260304 |

#### 请求体 (JSON)
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question | string | 是 | 用户提问 |
| images | string[] | 否 | Base64图片(最多3张) |
| session_id | string | 否 | 会话ID, 不传则自动生成 |

#### 响应
`json
{
  "code": 0,
  "msg": "success",
  "data": {
    "answer": "请参考以下步骤调节瞳距...",
    "session_id": "xxx",
    "timestamp": 1712345678
  }
}
`

---

## 核心处理流程 (pipeline.py 12步)

`
用户输入 (question + images + session_id)
  |
  + Step 1:  创建/获取会话 (DialogueManager)
  + Step 2:  构建 enhanced_question (从历史补全产品名)
  + Step 3:  意图识别 (IntentRecognizer)
  + Step 4:  CS模板匹配 (CSResponder)
  + Step 5:  图片理解 (VLMImageUnderstanding)
  + Step 6:  RAG检索 (HybridRetriever)
  |           + 向量检索(top_k=20) -> Cross-Encoder重排序(top_k=5)
  |           + 英文低分(0.01) -> EN_PRODUCT_MAP二次定位
  + Step 7:  按产品过滤 chunk
  + Step 8.1: 低分拦截 (返回Sorry)
  + Step 8.2: 产品验证 (映射表+手册名双保险)
  + Step 8.3: LLM生成 (AnswerAssembler)
  |           + grounding_light 验证 -> 不通过则降级到规则提取
  + Step 9:  后处理 (PostProcessor)
  + Step 10: 收集图片ID + 去重
  + Step 11: 清理Markdown前缀
  + Step 12: 事后幻觉检测 (数字/型号反向验证)
  |
  + 保存历史 + 返回 (answer, session_id)
`

### 幻觉抑制三防线

| 阶段 | 措施 |
|------|------|
| 事前 (Step 7-8) | 低分拦截 + 产品名验证 + EN_PRODUCT_MAP 二次定位 |
| 事中 (Step 8.3) | Prompt约束 + grounding_light 验证(英文0.3/中文0.25) |
| 事后 (Step 12) | 提取回答中型号/数字 -> 反向验证是否在原文出现 |

---

## 项目文件结构

## 项目文件结构

```
./
├── main.py                   →  启动入口
├── config.py                 →  统一配置
├── requirements.txt          →  依赖清单
├── .gitignore                →  忽略规则
├── README.md                 →  项目说明
├── AGENTS.md                 →  开发约束规则

├── api/                      →  API服务
│   ├── server.py             →  FastAPI端点
│   ├── schemas.py            →  数据模型
│   └── auth.py               →  Token鉴权

├── engine/                   →  核心引擎
│   ├── pipeline.py           →  12步流程编排
│   ├── cs_responder.py       →  客服模板匹配
│   ├── image_matcher.py      →  VLM图片匹配
│   │
│   ├── rag/                  →  RAG检索
│   │   ├── knowledge_base.py     →  语义向量检索
│   │   ├── hybrid_retriever.py   →  向量检索+重排序
│   │   └── text_image_mapper.py  →  文本↔图片ID映射
│   │
│   ├── generation/           →  答案生成
│   │   ├── answer_assembler.py   →  LLM+规则双通道
│   │   ├── llm_client.py     →  Ollama API客户端
│   │   └── post_processor.py     →  后处理
│   │
│   ├── multimodal/           →  多模态
│   │   ├── image_understanding.py  →  VLM图像理解
│   │   ├── intent_recognizer.py    →  意图识别
│   │   └── question_splitter.py    →  复合问题拆解
│   │
│   └── dialogue/             →  对话管理
│       └── manager.py        →  会话管理

├── data_processing/          →  知识库构建
│   ├── build_knowledge_base.py   →  构建入口
│   ├── text_cleaner.py       →  文本清洗
│   ├── text_chunker.py       →  文本分块
│   └── image_encoder.py      →  Base64编码

├── knowledge_base/           →  知识库配置
│   ├── cs_templates.json     →  客服模板
│   └── text_image_mapping.json   →  图文映射

├── tests/                    →  测试
│   ├── test_p0_regression.py     →  RAG回归测试
│   └── test_api.py           →  API测试

├── scripts/                  →  评估脚本
│   ├── batch_evaluate.py     →  批量评估
│   ├── generate_submission.py     →  全量评估
│   └── patch_run.py          →  补跑脚本

├── training/                 →  Embedding微调
│   └── embedding_trainer.py

└── static/                   →  前端
    └── index.html            →  聊天页面
```
## 批量评估

`ash
# 测试 1-10 题
python scripts/batch_evaluate.py --start 1 --end 10

# 全量 400 题评估
python scripts/generate_submission.py
`

输出 
esults/submission_result.csv (格式: id, ret)，与赛题提交格式一致。

---

## 注意事项

- 大文件 (2608张插图、图片索引) 和竞赛素材 (手册、数据) 已被 .gitignore 排除，克隆后需自行准备
- 克隆后需运行 python data_processing/build_knowledge_base.py 重新生成
- 向量数据库存储在 %TEMP%\dl_kb_chroma (0.67MB)
- Embedding 模型: BAAI/bge-small-zh-v1.5 (512维)
- 重排序模型: BAAI/bge-reranker-v2-m3 (可选, 2.2GB)
- 20 份中文手册 -> 152 个文本块
