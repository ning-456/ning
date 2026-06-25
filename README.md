# 多模态客服智能体 (Multimodal Customer Service Agent)

基于 **检索增强生成（RAG）** 与 **多模态大语言模型** 的智能客服系统，支持图文混合问答、多轮对话、意图识别与知识库检索。

---

## 项目架构

采用 **四层架构 + 五大模块** 设计：

### 四层架构

| 层级 | 职责 | 核心组件 |
|------|------|----------|
| **API 层** | HTTP 接口 & 身份认证 | FastAPI, Pydantic 模型, Token 鉴权 |
| **引擎层** | 核心业务逻辑编排 | 对话管理、意图识别、RAG 检索、生成后处理 |
| **数据处理层** | 知识库预处理 | 文本分块、问句拆分、向量索引构建 |
| **基础设施层** | 存储与外部服务 | ChromaDB, OpenAI API, Embedding 模型 |

### 五大模块

| 模块 | 文件路径 | 功能说明 |
|------|----------|----------|
| **RAG 检索** | `engine/rag/` | 混合检索（向量 + BM25 + RRF 重排序）、图文映射查询 |
| **对话管理** | `engine/dialogue/` | 多轮会话管理、意图识别（售后/咨询/闲聊/其他） |
| **生成处理** | `engine/generation/` | LLM 回答生成、后处理（插入 `<PIC>` 图片标签） |
| **多模态** | `engine/multimodal/` | 图片描述生成、多图融合理解 |
| **数据处理** | `data_processing/` | 知识库文本分块、用户多问句拆分 |

---

## 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | 3.10+ |
| pip | 21.0+（支持 `pyproject.toml`） |
| 操作系统 | Windows / Linux / macOS |

### 安装依赖

```bash
# 克隆项目后，在项目根目录执行
pip install -r requirements.txt
```

> **注意**：`sentence-transformers` 首次运行时会自动下载 Embedding 模型（约 100MB），请确保网络通畅。如无法访问 HuggingFace，可通过 `config.py` 中的 `EMBEDDING_MODEL` 配置镜像源。

---

## 快速开始

### 1. 配置 API 密钥

编辑 `config.py` 或设置环境变量：

```bash
# 设置 LLM API 密钥（必填）
set LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：自定义 API 地址和模型
set LLM_API_BASE=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
```

> 支持使用任何兼容 OpenAI 格式的 API（如 Azure OpenAI、本地 vLLM 部署等）。

### 2. 构建知识库

在项目根目录准备以下资源：

```
手册/              # 产品手册/Markdown 文件目录
手册/插图/          # 手册中的插图（PNG/JPG）
question_public.csv # 公开测试问题集
```

执行知识库构建脚本（由 `data_processing/` 模块提供）：

```bash
python -c "from data_processing.build_knowledge_base import build; build()"
```

构建完成后将在 `knowledge_base/` 目录下生成：
- `chroma_db/` — 向量数据库
- `image_index.json` — 图片索引
- `text_image_mapping.json` — 图文映射关系

### 3. 启动服务

```bash
python main.py
```

服务默认监听 `http://0.0.0.0:8000`，启动后可通过 `GET /health` 验证。

### 4. 测试服务

```bash
# 健康检查
curl http://localhost:8000/health

# 发送客服咨询
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer sk_customer_20260304" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"产品无法开机怎么办？\", \"images\": [], \"session_id\": null}"
```

---

## API 文档

### 健康检查

```
GET /health
```

**响应示例：**

```json
{
  "status": "ok",
  "timestamp": 1712345678
}
```

### 客服咨询

```
POST /chat
```

#### 请求头

| 字段 | 必填 | 说明 |
|------|------|------|
| `Authorization` | 是 | Bearer Token，格式为 `Bearer <token>` |

#### 请求体 (JSON)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | `string` | 是 | 用户提问文本，至少 1 个字符 |
| `images` | `array[string]` | 否 | Base64 编码的图片列表，最多 3 张 |
| `session_id` | `string` | 否 | 会话 ID，不传则自动生成新会话 |
| `stream` | `boolean` | 否 | 固定为 `false`，暂不支持流式 |

#### 响应格式

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "answer": "您好，针对您的问题，建议您尝试以下操作：...\\n<PIC>插图/重启步骤.png</PIC>",
    "session_id": "sess_abc123def456",
    "timestamp": 1712345678
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | `int` | 状态码（0 成功，401 鉴权失败，400 参数错误，500 服务内部错误） |
| `msg` | `string` | 状态描述 |
| `data.answer` | `string` | 客服回答，含 `<PIC>图片路径</PIC>` 图片标签 |
| `data.session_id` | `string` | 本次会话 ID |
| `data.timestamp` | `int` | 秒级 Unix 时间戳 |

#### 错误响应示例

**401 Token 缺失：**
```json
{
  "detail": "Missing or invalid authorization token"
}
```

**400 验证错误：**
```json
{
  "detail": [
    {
      "loc": ["body", "question"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 项目结构

```
├── main.py                          # 项目入口
├── config.py                        # 统一配置文件
├── requirements.txt                 # 依赖清单
├── README.md                        # 项目文档
│
├── api/                             # API 层
│   ├── server.py                    # FastAPI 应用 & 路由
│   ├── schemas.py                   # Pydantic 请求/响应模型
│   └── __init__.py
│
├── engine/                          # 引擎层
│   ├── dialogue/                    # 对话管理模块
│   │   ├── session.py              # 会话管理（SessionManager）
│   │   ├── intent.py               # 意图识别（IntentRecognizer）
│   │   └── __init__.py
│   ├── rag/                         # 检索增强生成模块
│   │   ├── hybrid_search.py        # 混合检索（向量+BM25+RRF）
│   │   ├── image_index.py          # 图文索引管理
│   │   └── __init__.py
│   ├── generation/                  # 生成后处理模块
│   │   ├── post_processing.py      # 回答后处理（PIC标签插入）
│   │   └── __init__.py
│   ├── multimodal/                  # 多模态处理模块
│   │   ├── image_description.py    # 图片描述生成
│   │   └── __init__.py
│   └── __init__.py
│
├── data_processing/                 # 数据处理层
│   ├── text_chunking.py            # 文本分块
│   ├── question_splitting.py       # 问句拆分
│   └── __init__.py
│
├── tests/                           # 测试目录
│   ├── test_api.py                 # API 接口测试
│   ├── test_rag.py                 # RAG 检索测试
│   ├── test_pipeline.py            # 全流程测试
│   └── __init__.py
│
├── knowledge_base/                  # 知识库（构建生成）
│   ├── chroma_db/                  # 向量数据库
│   ├── image_index.json            # 图片索引
│   └── text_image_mapping.json     # 图文映射关系
│
├── 手册/                            # 产品手册（原始数据）
│   ├── 产品说明.md
│   ├── 常见问题.md
│   └── 插图/
│       ├── 开机步骤.png
│       └── 故障排除.png
│
├── question_public.csv              # 公开测试问题集
└── submission_example.csv           # 提交示例
```

---

## 注意事项

### Token 认证

- 所有 `/chat` 请求必须在 HTTP 头中携带 `Authorization: Bearer <token>`
- 默认 Token 为 `sk_customer_20260304`（可在 `config.py` 中修改）
- Token 校验失败返回 `401 Unauthorized`

### 超时设置

| 场景 | 默认超时 | 说明 |
|------|----------|------|
| 纯文本问答 | 20 秒 | 无图片时的回答生成 |
| 图文混合问答 | 30 秒 | 含图片时需要额外时间处理视觉信息 |

可通过 `config.py` 中的 `TEXT_TIMEOUT` 和 `IMAGE_TIMEOUT` 调整。

### 图片格式

- 图片以 **Base64 编码** 传输，不含 `data:image/...;base64,` 前缀
- 支持的图片格式：PNG、JPEG、WebP
- 单次请求最多携带 **3 张** 图片
- 单张图片大小建议不超过 5MB（Base64 编码后约 6.7MB）

### 会话管理

- 服务端自动管理会话，不传 `session_id` 时自动生成
- 会话默认超时时间为 3600 秒（1 小时），超时后自动清理
- 最多保留最近 5 轮对话历史
- 建议客户端缓存 `session_id` 以保持多轮对话连贯性

### 知识库

- 首次使用前必须构建知识库（向量数据库 + 图片索引）
- 知识库构建依赖 `sentence-transformers` 模型，首次运行需下载
- 支持增量更新：添加新手册后重新运行构建脚本即可

### 部署建议

- 生产环境建议使用 `gunicorn` + `uvicorn` 多进程部署
- 可配合 Docker 容器化部署，确保 Embedding 模型路径映射正确
- 建议配置反向代理（Nginx）以支持 HTTPS 和负载均衡

---

## 开发与测试

### 运行测试

```bash
# 安装测试依赖
pip install pytest httpx pytest-asyncio

# 运行全部测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_api.py -v

# 运行单个测试用例
pytest tests/test_api.py::test_health_check -v
```

### 代码格式化

```bash
# 安装 ruff
pip install ruff

# 代码检查
ruff check .

# 代码格式化
ruff format .
```

---

*项目基于 Python 3.10+ 开发，遵循 MIT 协议。*

---

## 批量评估

对赛题的400道题批量处理并生成提交文件：

```bash
# 构建知识库后运行
python scripts/batch_evaluate.py

# 指定输入/输出文件
python scripts/batch_evaluate.py --input question_public.csv --output submission_result.csv

# 调试：只处理前10题
python scripts/batch_evaluate.py --start 1 --end 10
```

输出 CSV 格式：`id,ret` — 与赛题提交格式一致。

---

## Embedding 模型领域微调

在手册数据上微调 Embedding 模型，提升领域检索效果：

```bash
# Step 1: 准备训练数据（从手册文本生成三元组）
python training/prepare_training_data.py

# Step 2: 开始微调
python training/embedding_trainer.py
```

微调完成后，修改 `config.py` 中的 `EMBEDDING_MODEL` 为 `training/finetuned_embedding_model`，然后重新构建知识库：

```bash
python data_processing/build_knowledge_base.py
```

---

## LLM 开关

系统默认**不依赖外部 LLM API**，完全自包含运行。

如需使用 LLM 提升生成质量，设置环境变量：

```bash
set USE_LLM=true
set LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

或修改 `config.py`：

```python
USE_LLM = True
LLM_API_KEY = "sk-..."
```

---


## 环境准备

### 1. 创建 GitHub 仓库（首次提交用）

`ash
# 已在项目目录下
cd C:\Users\17229\Desktop\深度学习大作业

# 初始化（已完成）
git init

# 暂存所有文件
git add .

# 创建提交
git commit -m "init: 多模态客服智能体 v1.0"
`

### 2. 推送到 GitHub

`ash
# 方式一：GitHub CLI（需先登录）
gh auth login
gh repo create <仓库名> --public --source=. --push

# 方式二：手动创建
# 1. 浏览器打开 https://github.com/new
# 2. 创建空仓库（不要勾选 README/LICENSE/.gitignore）
# 3. 复制仓库 URL，运行：
git remote add origin https://github.com/<用户名>/<仓库名>.git
git branch -M main
git push -u origin main
`

### 3. 克隆后运行

`ash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 构建知识库（生成 image_index.json + 向量索引）
python data_processing/build_knowledge_base.py

# 3. 启动服务
python main.py
`

### 注意事项

- knowledge_base/image_index.json（194MB, 2608张图片Base64）和 手册/插图/（140MB）被 .gitignore 排除
- 克隆后需运行 uild_knowledge_base.py 重新生成，或手动复制这两个文件
- 向量数据库实际存储在 %TEMP%\dl_kb_chroma，已排除在版本控制之外
## 实际项目结构

```
├── main.py                          # 项目入口
├── config.py                        # 统一配置
├── requirements.txt                 # 依赖清单
├── README.md
│
├── api/
│   ├── server.py                    # FastAPI 服务 (端口8000)
│   ├── schemas.py                   # 请求/响应模型
│   └── auth.py                      # Token 鉴权
│
├── engine/
│   ├── pipeline.py                  # 核心流程编排
│   ├── cs_responder.py              # 通用客服模板匹配
│   ├── image_matcher.py             # CLIP 图片匹配
│   ├── dialogue/manager.py          # 多轮对话管理
│   ├── multimodal/
│   │   ├── image_understanding.py   # 图片理解
│   │   ├── question_splitter.py     # 多问题拆分
│   │   └── intent_recognizer.py     # 意图识别
│   ├── rag/
│   │   ├── knowledge_base.py        # FAISS 向量库
│   │   ├── hybrid_retriever.py      # 混合检索(BM25+向量+RRF)
│   │   └── text_image_mapper.py     # 图文映射
│   └── generation/
│       ├── answer_assembler.py      # 答案组装
│       ├── llm_client.py            # LLM 调用封装
│       ├── post_processor.py        # 后处理(<PIC>标签)
│       └── prompt_builder.py        # Prompt 构建
│
├── data_processing/
│   ├── text_cleaner.py              # 文本清洗
│   ├── text_chunker.py              # 文本分块
│   ├── image_encoder.py             # 图片编码
│   └── build_knowledge_base.py      # 知识库构建入口
│
├── scripts/
│   └── batch_evaluate.py            # 批量评估脚本
│
├── training/
│   ├── prepare_training_data.py     # 训练数据准备
│   └── embedding_trainer.py         # Embedding 微调
│
├── tests/
│   ├── test_api.py
│   ├── test_rag.py
│   └── test_pipeline.py
│
├── knowledge_base/
│   ├── image_index.json             # 图片索引
│   ├── text_image_mapping.json      # 图文映射
│   └── cs_templates.json            # 客服模板
│
├── static/
│   └── index.html                   # 前端界面
│
├── 手册/                            # 产品手册 (txt)
│   └── 插图/                        # 手册插图 (2608张)
│
├── question_public.csv              # 赛题(400道)
└── submission_example.csv           # 提交示例
```