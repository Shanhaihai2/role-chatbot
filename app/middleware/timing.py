import time
from fastapi import Request
from app.core.logger import logger

async def timing_middleware(request: Request, call_next):
    """记录每个请求的处理时间"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"状态: {response.status_code} "
        f"耗时: {process_time:.3f}s"
    )
    return response