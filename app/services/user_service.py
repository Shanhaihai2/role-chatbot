# app/services/user_service.py
import jwt
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.config import settings
from app.core.logger import logger

def hash_password(password: str) -> str:
    """对密码进行哈希加密（使用 werkzeug，无长度限制）"""
    return generate_password_hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    return check_password_hash(hashed_password, plain_password)

def create_user(username: str, password: str, db: Session) -> User:
    """注册新用户。如果用户名已存在，返回 None。"""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        logger.warning(f"注册失败：用户名 {username} 已存在")
        return None

    user = User(
        username=username,
        hashed_password=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"新用户注册成功：{username}（ID={user.id}）")
    return user

def authenticate_user(username: str, password: str, db: Session) -> str | None:
    """验证用户登录。成功返回 JWT Token，失败返回 None。"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"登录失败：用户名 {username} 不存在")
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning(f"登录失败：用户名 {username} 密码错误")
        return None

    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    logger.info(f"用户 {username} 登录成功，Token 已生成")
    return token

def get_user_by_id(user_id: int, db: Session) -> User | None:
    """根据用户ID查询用户"""
    return db.query(User).filter(User.id == user_id).first()