from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.models.role import Role
from app.core.response import ApiResponse
from app.agents.role_agent import role_agent

router = APIRouter()

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户发送的消息")

@router.post("/chat/{role_id}")
async def chat_with_role(
    role_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """与指定角色对话"""
    # 1. 查找角色
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if not role.persona_instruction:
        raise HTTPException(status_code=400, detail="角色尚未提取人设，请先上传素材并提取人设")

    # 2. 调用Agent
    result = role_agent.invoke({
        "role_id": role_id,
        "role_name": role.name,
        "persona": role.persona_instruction,
        "user_message": request.message,
        "history": [],      # 暂时无历史，第5天会加入记忆
        "retrieved_materials": "",
        "final_response": ""
    })

    return ApiResponse.ok(data={
        "role_id": role_id,
        "role_name": role.name,
        "reply": result["final_response"]
    })