from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.response import ApiResponse
from app.core.logger import logger
from app.services.user_service import create_user, authenticate_user
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter()

# ====== 请求体模型 ======
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=72, description="密码")

class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

# ====== 注册 ======
@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    logger.info(f"收到注册请求：username={request.username}")
    user = create_user(request.username, request.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    return ApiResponse.ok(
        data={"user_id": user.id, "username": user.username},
        msg="注册成功"
    )

# ====== 登录 ======
@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录，返回 JWT Token"""
    logger.info(f"收到登录请求：username={request.username}")
    token = authenticate_user(request.username, request.password, db)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return ApiResponse.ok(
        data={"token": token, "token_type": "bearer"},
        msg="登录成功"
    )

# ====== 获取当前用户信息 ======
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户的信息"""
    logger.info(f"用户 {current_user.username} 查询自己的信息")
    return ApiResponse.ok(data={
        "user_id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    })