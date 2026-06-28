"""FastAPI应用入口 - 多模态客服智能体API"""
import time, json, base64
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse, Response
from config import API_HOST, API_PORT, IMAGE_INDEX_PATH
from api.schemas import ChatRequest, ChatResponse, ChatResponseData
from pydantic import BaseModel
from api.auth import verify_token
import requests
import config
from engine.pipeline import CustomerServicePipeline


class SwitchModel(BaseModel):
    model: str


_pipeline = None
def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = CustomerServicePipeline()
    return _pipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    pipe = get_pipeline()
    pipe.load_knowledge_base()
    yield

app = FastAPI(title="多模态客服智能体API", lifespan=lifespan)

@app.get("/health", tags=["系统"])
async def health():
    p = get_pipeline()
    return {"status":"ok","timestamp":int(time.time()),
            "active_sessions":p.dialogue_manager.get_session_count() if p.dialogue_manager else 0,
            "kb_loaded":p._kb_loaded}

@app.post("/chat", response_model=ChatResponse, tags=["客服"])
async def chat(request: ChatRequest, token: str = Depends(verify_token)):
    p = get_pipeline()
    answer, sid = p.process(
        question=request.question,
        images=request.images if request.images else [],
        session_id=request.session_id)
    return ChatResponse(code=0, msg="success",
        data=ChatResponseData(answer=answer, session_id=sid, timestamp=int(time.time())))

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    idx = Path(__file__).parent.parent / "static" / "index.html"
    if idx.exists():
        return HTMLResponse(content=idx.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend not ready</h1>")

@app.get("/api/models", tags=["系统"])
async def list_models():
    """获取 Ollama 可用模型列表及当前选中"""
    try:
        r = requests.get(config.LLM_API_BASE.replace("/v1", "") + "/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        models = []
    return {"models": models, "current_llm": config.CURRENT_LLM_MODEL, "current_vlm": config.CURRENT_VLM_MODEL}


@app.post("/api/models/switch", tags=["系统"])
async def switch_model(data: SwitchModel):
    """切换 LLM + VLM 运行时模型"""
    config.CURRENT_LLM_MODEL = data.model
    config.CURRENT_VLM_MODEL = data.model
    print(f"[API] 模型已切换: LLM={config.CURRENT_LLM_MODEL}, VLM={config.CURRENT_VLM_MODEL}")
    return {"ok": True, "current_llm": config.CURRENT_LLM_MODEL, "current_vlm": config.CURRENT_VLM_MODEL}


@app.get("/api/image/{image_id}", include_in_schema=False)
async def get_image(image_id: str):
    try:
        with open(IMAGE_INDEX_PATH, "r", encoding="utf-8") as f:
            idx = json.load(f)
        if image_id not in idx:
            return Response(status_code=404)
        b64 = idx[image_id]
        if "," in b64:
            h, d = b64.split(",", 1)
            mime = h.replace("data:","").replace(";base64","")
        else:
            mime, d = "image/png", b64
        return Response(content=base64.b64decode(d), media_type=mime)
    except:
        return Response(status_code=404)
