"""多模态客服智能体 - 项目入口
一键启动服务: python main.py
"""
import uvicorn
from config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )
