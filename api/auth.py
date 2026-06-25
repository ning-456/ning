from fastapi import Header, HTTPException
from typing import Annotated

import config


async def verify_token(
    authorization: Annotated[str, Header(description="Bearer token认证")] = "",
) -> str:
    """验证 Bearer Token 的 FastAPI 依赖函数。

    从 Authorization 头中提取 Bearer token，与 config.API_TOKEN 比较。
    认证失败时抛出 401 HTTPException。

    Args:
        authorization: Authorization 请求头内容

    Returns:
        验证通过的 token 字符串

    Raises:
        HTTPException: 401 - token缺失或无效
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token is empty")

    if token != config.API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

    return token
