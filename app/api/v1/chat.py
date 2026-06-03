from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.models.role import Role
from app.core.response import ApiResponse
from app.agents.role_agent import role_agent
from app.utils.auth import get_current_user
from app.models.user import User
from app.core.logger import logger

router = APIRouter()

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户发送的消息")

@router.post("/chat/{role_id}")
async def chat_with_role(
    role_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 新增：需要登录
):
    """与指定角色对话（需要登录）"""
    logger.info(f"用户 {current_user.username} 请求与角色 {role_id} 对话：{request.message[:30]}...")
    # 1. 查找角色
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        logger.warning(f"对话失败：角色 {role_id} 不存在")
        raise HTTPException(status_code=404, detail="角色不存在")
    if not role.persona_instruction:
        raise HTTPException(status_code=400, detail="角色尚未提取人设")

    # 2. 调用Agent
    result = role_agent.invoke({
        "role_id": role_id,
        "role_name": role.name,
        "persona": role.persona_instruction,
        "user_message": request.message,
        "history": [],
        "retrieved_materials": "",
        "retrieved_memories": "",
        "final_response": ""
    })
    logger.info(f"角色 {role_id} 回复生成完成，长度：{len(result['final_response'])}")

    return ApiResponse.ok(data={
        "role_id": role_id,
        "role_name": role.name,
        "reply": result["final_response"]
    })