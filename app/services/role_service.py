from sqlalchemy.orm import Session
from app.models.role import Role
from app.agents.persona_agent import generate_persona_instruction
from app.core.logger import logger

def update_role(role_id: int, update_data: dict, db: Session):
    """
    更新角色信息。
    返回更新后的角色对象，如果角色不存在返回 None。
    如果更新了 raw_material，会重新提取 persona_instruction。
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        logger.warning(f"更新角色失败：角色 {role_id} 不存在")
        return None

    # 如果更新了素材，需要重新提取人设
    if "raw_material" in update_data and update_data["raw_material"]:
        logger.info(f"角色 {role_id} 素材已更新，重新提取人设...")
        role.raw_material = update_data["raw_material"]
        try:
            role.persona_instruction = generate_persona_instruction(update_data["raw_material"])
            logger.info(f"角色 {role_id} 人设重新提取成功")
        except Exception as e:
            logger.error(f"角色 {role_id} 人设提取失败：{e}")
            # 提取失败时不阻断更新，保留原人设

    # 更新其他允许修改的字段
    if "name" in update_data and update_data["name"]:
        role.name = update_data["name"]
    if "description" in update_data:
        role.description = update_data["description"]

    db.commit()
    db.refresh(role)
    logger.info(f"角色 {role_id} 更新成功")
    return role


def delete_role(role_id: int, db: Session):
    """
    删除角色。
    返回被删除的角色名称，如果角色不存在返回 None。
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        logger.warning(f"删除角色失败：角色 {role_id} 不存在")
        return None

    role_name = role.name
    db.delete(role)
    db.commit()
    logger.info(f"角色 {role_id}（{role_name}）已删除")
    return role_name