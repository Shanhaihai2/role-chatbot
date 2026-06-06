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
from app.utils.session import add_message, get_history
from fastapi.responses import StreamingResponse
from app.services.stream_service import generate_stream

router = APIRouter()

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户发送的消息")

@router.post("/chat/{role_id}")
async def chat_with_role(
    role_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
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
    
    # 从服务端获取历史
    history = get_history(current_user.id, role_id)
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    # 调用Agent
    result = role_agent.invoke({
        "role_id": role_id,
        "user_id": str(current_user.id),
        "role_name": role.name,
        "persona": role.persona_instruction,
        "user_message": request.message,
        "history": history_text,
        "retrieved_materials": "",
        "retrieved_memories": "",
        "final_response": ""
    })
    reply = result["final_response"]
     # 存入历史
    add_message(current_user.id, role_id, "user", request.message)
    add_message(current_user.id, role_id, "ai", reply)

    logger.info(f"角色 {role_id} 回复生成完成，长度：{len(result['final_response'])}")

    return ApiResponse.ok(data={
        "role_id": role_id,
        "role_name": role.name,
        "reply": reply
    })

#流式输出
@router.post("/chat/{role_id}/stream")
async def chat_with_role_stream(
    role_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """与角色对话（流式输出）"""
    logger.info(f"用户 {current_user.username} 请求流式对话，角色={role_id}")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role or not role.persona_instruction:
        raise HTTPException(status_code=400, detail="角色不可用")

    history = get_history(current_user.id, role_id)
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    add_message(current_user.id, role_id, "user", request.message)

    async def event_stream():
        collected = ""
        async for token in generate_stream(
            role_id, str(current_user.id), role.name, role.persona_instruction,
            request.message, history_text
        ):
            collected += token
            yield f"data: {token}\n\n"
        add_message(current_user.id, role_id, "ai", collected)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")