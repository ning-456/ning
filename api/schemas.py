from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """客服请求模型"""
    question: str = Field(..., min_length=1, description="用户提问文本")
    images: list[str] = Field(default_factory=list, max_length=3, description="Base64图片列表(0-3张)")
    session_id: Optional[str] = Field(None, description="会话ID，不传则自动生成")
    stream: bool = Field(False, description="是否流式响应，固定为false")


class ChatResponseData(BaseModel):
    """客服响应数据模型"""
    answer: str = Field(..., description="客服回答内容(含<PIC>标签)")
    session_id: str = Field(..., description="当前会话ID")
    timestamp: int = Field(..., description="秒级时间戳")


class ChatResponse(BaseModel):
    """客服响应模型"""
    code: int = Field(0, description="状态码")
    msg: str = Field("success", description="状态描述")
    data: ChatResponseData
