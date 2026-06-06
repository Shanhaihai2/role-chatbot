from typing import AsyncGenerator
from langchain_core.messages import AIMessageChunk
from app.agents.role_agent import role_agent
from app.core.logger import logger

async def generate_stream(
    role_id: int, user_id: str, role_name: str, persona: str,
    message: str, history: str
) -> AsyncGenerator[str, None]:
    """流式生成角色回复"""
    logger.info(f"开始流式生成，角色={role_name}")
    try:
        async for chunk in role_agent.astream({
            "role_id": role_id,
            "user_id": user_id,
            "role_name": role_name,
            "persona": persona,
            "user_message": message,
            "history": history,
            "retrieved_materials": "",
            "retrieved_memories": "",
            "final_response": ""
        }, stream_mode="messages"):
            if isinstance(chunk, tuple) and len(chunk) >= 2:
                msg = chunk[0]
                metadata = chunk[1]
                # 只保留 generate_response 节点的输出
                if metadata.get("langgraph_node") == "generate_response":
                    if isinstance(msg, AIMessageChunk) and msg.content:
                        yield msg.content
    except Exception as e:
        logger.error(f"流式生成出错: {e}")
        yield f"[生成出错: {str(e)}]"