from app.core.database import SessionLocal
from app.models.role import Role
from app.core.logger import logger

# 用户会话状态（内存存储）
# 格式：{openid: {"state": "idle"|"awaiting_material", "temp_name": "角色名", "selected_role_id": 1}}
user_sessions = {}

def get_user_roles(openid: str) -> list:
    """获取用户创建的角色列表"""
    db = SessionLocal()
    roles = db.query(Role).filter(Role.creator_openid == openid).all()
    db.close()
    return roles

def get_user_session(openid: str) -> dict:
    """获取用户会话状态，没有则初始化"""
    if openid not in user_sessions:
        user_sessions[openid] = {"state": "idle", "temp_name": None, "selected_role_id": None}
    return user_sessions[openid]

def handle_command(openid: str, content: str) -> str:
    """
    解析用户输入，如果是命令则执行并返回回复文本。
    如果不是命令，返回 None，交由对话处理。
    """
    session = get_user_session(openid)
    content = content.strip()

    # ===== 创建角色：引导发送素材 =====
    if content.startswith("/create") or content.startswith("创建"):
        parts = content.split(maxsplit=1)
        if len(parts) < 2:
            return "请按格式输入：/create 角色名"
        role_name = parts[1].strip()
        session["state"] = "awaiting_material"
        session["temp_name"] = role_name
        logger.info(f"用户 {openid} 开始创建角色：{role_name}")
        return f"好的，请发送「{role_name}」的对话素材文件（TXT），或直接发送文本内容。"

    # ===== 上传素材：处理待创建状态 =====
    if session["state"] == "awaiting_material":
        role_name = session["temp_name"]
        raw_text = content
        db = SessionLocal()
        role = Role(name=role_name, raw_material=raw_text, creator_openid=openid)
        db.add(role)
        db.commit()
        db.refresh(role)
    
        # 自动提取人设
        from app.agents.persona_agent import generate_persona_instruction
        try:
            persona = generate_persona_instruction(raw_text)
            role.persona_instruction = persona
            db.commit()
            db.refresh(role)
            logger.info(f"用户 {openid} 创建角色成功：{role_name}，人设已自动提取")
        except Exception as e:
            logger.error(f"人设提取失败：{e}")
            # 即使提取失败，角色也已创建，只是没有自动人设
    
        db.close()
        session["state"] = "idle"
        session["temp_name"] = None
        return f"角色「{role_name}」创建成功！人设已自动生成。发送「/select {role.id}」来和ta对话吧。"

    # ===== 查看角色列表 =====
    if content in ["/roles", "我的角色", "角色列表"]:
        roles = get_user_roles(openid)
        if not roles:
            return "您还没有创建任何角色。发送「/create 角色名」来创建一个吧！"
        lines = [f"{i+1}. {r.name}" for i, r in enumerate(roles)]
        return "您的角色列表：\n" + "\n".join(lines) + "\n\n发送「/select 编号」选择一个角色。"
    

    # ===== 选择角色 =====
    if content.startswith("/select") or content.startswith("选择"):
        parts = content.replace("/select", "").replace("选择", "").strip()
        try:
            index = int(parts) - 1
            roles = get_user_roles(openid)
            if 0 <= index < len(roles):
                session["selected_role_id"] = roles[index].id
                # 清除旧角色的短期历史
                from app.utils.session import clear_history
                clear_history(openid, roles[index].id)
                logger.info(f"用户 {openid} 选择角色：{roles[index].name}，已清除旧历史")
                return f"已切换到「{roles[index].name}」，现在开始对话吧！"
        except ValueError:
            pass
        return "请按格式输入：/select 编号"

    # ===== 删除角色 =====
    if content.startswith("/delete") or content.startswith("删除"):
        parts = content.replace("/delete", "").replace("删除", "").strip()
        try:
            index = int(parts) - 1
            roles = get_user_roles(openid)
            if 0 <= index < len(roles):
                role = roles[index]
                db = SessionLocal()
                db.query(Role).filter(Role.id == role.id, Role.creator_openid == openid).delete()
                db.commit()
                db.close()

                # 清除 Chroma 中的长期记忆集合
                try:
                    import chromadb
                    from app.core.config import settings
                    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
                    collection_name = f"role_{role.id}_memory_user_{openid}"
                    client.delete_collection(collection_name)
                    logger.info(f"已清除角色 {role.id} 的长期记忆集合")
                except Exception as e:
                    logger.warning(f"清除 Chroma 记忆失败（可能集合不存在）：{e}")

                if session["selected_role_id"] == role.id:
                    session["selected_role_id"] = None
                logger.info(f"用户 {openid} 删除角色：{role.name}")
                return f"角色「{role.name}」已删除，相关记忆已清除。"
        except ValueError:
            pass
        return "请按格式输入：/delete 编号"

    # 不是命令，返回 None 交由对话处理
    return None