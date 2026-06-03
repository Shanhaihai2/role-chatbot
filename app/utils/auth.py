import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.core.logger import logger

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    从请求头中解析 JWT Token，返回当前用户对象。
    如果 Token 无效或用户不存在，抛出 401。
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            logger.warning("Token 中未包含 user_id")
            raise HTTPException(status_code=401, detail="无效的访问令牌")
    except jwt.ExpiredSignatureError:
        logger.warning("Token 已过期")
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        logger.warning("Token 无效")
        raise HTTPException(status_code=401, detail="无效的访问令牌")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Token 中的用户 {user_id} 不存在")
        raise HTTPException(status_code=401, detail="用户不存在")

    return user