from fastapi import APIRouter, Request, Query, HTTPException
from app.core.config import settings
from app.core.logger import logger
from app.services.wechat_service import verify_signature, send_custom_message
from app.agents.role_agent import role_agent
from fastapi.responses import PlainTextResponse
from app.utils.wechat_commands import handle_command, get_user_session
from app.utils.session import get_history, add_message

router = APIRouter()
# 已处理消息ID集合（内存去重）
processed_msg_ids = set()
# 默认使用的角色 ID（可后续扩展为多角色）
DEFAULT_ROLE_ID = 1
DEFAULT_ROLE_NAME = "小明"
DEFAULT_PERSONA = "你是一个叫小明的角色..."

@router.get("/wechat")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """
    微信服务器验证接口（首次接入时使用）。
    验证成功返回 echostr，验证失败返回错误信息。
    """
    logger.info("收到微信服务器验证请求")
    if verify_signature(signature, timestamp, nonce):
        logger.info("微信服务器验证成功")
        return PlainTextResponse(content=echostr)
    logger.warning("微信服务器验证失败：签名不匹配")
    raise HTTPException(status_code=403, detail="签名验证失败")

@router.post("/wechat")
async def wechat_message(request: Request):
    """
    接收微信用户发来的消息，调用角色 Agent 生成回复。
    """
    # 解析微信发来的 XML 消息体
    body = await request.body()
    from xml.etree.ElementTree import fromstring
    xml_data = fromstring(body)

    # 提取消息ID用于去重
    msg_id_elem = xml_data.find("MsgId")
    if msg_id_elem is not None:
        msg_id = msg_id_elem.text
        if msg_id in processed_msg_ids:
            logger.info(f"消息 {msg_id} 已处理过，跳过")
            return "success"
        processed_msg_ids.add(msg_id)
        # 防止集合无限增长，可定期清理（简单实现：超过1000条时清空）
        if len(processed_msg_ids) > 1000:
            processed_msg_ids.clear()

    # 只处理文本消息
    msg_type = xml_data.find("MsgType")
    if msg_type is None or msg_type.text != "text":
        return "success"

    user_openid = xml_data.find("FromUserName").text
    user_message = xml_data.find("Content").text
    logger.info(f"收到微信用户消息：openid={user_openid}, content={user_message}")

    # ===== 第一步：尝试命令解析 =====
    cmd_reply = handle_command(user_openid, user_message)
    if cmd_reply is not None:
        send_custom_message(user_openid, cmd_reply)
        return "success"
    
    # ===== 第二步：正常对话 =====
    session = get_user_session(user_openid)
    selected_role_id = session.get("selected_role_id")

    if not selected_role_id:
        send_custom_message(user_openid, "请先选择一个角色。发送「我的角色」查看列表，或发送「/create 角色名」创建新角色。")
        return "success"
    

    # 调用角色 Agent 生成回复
    try:
        from app.core.database import SessionLocal
        from app.models.role import Role
        db = SessionLocal()
        
        # 查找第一个有人设的角色
        role = db.query(Role).filter(Role.id == selected_role_id).first()
        db.close()
        history = get_history(user_openid, selected_role_id)  # 用 openid 作为 user_id
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

        if not role or not role.persona_instruction:
            send_custom_message(user_openid, "所选角色不可用，请重新选择。")
            return "success"
        result = role_agent.invoke({
            "role_id": role.id,
            "user_id": user_openid,
            "role_name": role.name,
            "persona": role.persona_instruction,
            "user_message": user_message,
            "history": history_text,
            "retrieved_materials": "",
            "retrieved_memories": "",
            "final_response": ""
        })
        # 调用后存入历史
        add_message(user_openid, selected_role_id, "user", user_message)
        add_message(user_openid, selected_role_id, "ai", result["final_response"])
        reply = result["final_response"]
    except Exception as e:
        logger.error(f"角色 Agent 生成回复失败：{e}")
        reply = "抱歉，我暂时无法回复，请稍后再试。"

    # 通过客服消息发送回复
    send_custom_message(user_openid, reply)

    return "success"