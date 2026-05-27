from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.response import ApiResponse
from app.api.v1.health import router as health_router
from app.api.v1.roles import router as roles_router
from app.api.v1.chat import router as chat_router
from contextlib import asynccontextmanager
from app.core.database import Base, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表
    Base.metadata.create_all(bind=engine)
    # 预加载 Embedding 模型
    from app.services.material_service import embeddings
    print("✅ Embedding 模型已加载")
    from app.models import memory# 确保模型被注册

    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")

# 全局异常处理器
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(code=exc.status_code, msg=exc.detail).model_dump()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=500, msg="服务器内部错误").model_dump()
    )

@app.get("/")
async def root():
    return ApiResponse.ok(data={"app": settings.APP_NAME, "version": settings.APP_VERSION})