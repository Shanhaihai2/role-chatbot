from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.role import Role
from app.core.response import ApiResponse
from app.agents.persona_agent import generate_persona_instruction
from app.services.material_service import build_role_knowledge_base
from app.services.role_service import update_role, delete_role, update_persona
from app.models.request import RoleUpdate, PersonaUpdate
from app.core.logger import logger
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/roles")
async def create_role(
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),   # 暂时只接受一个文本文件
    db: Session = Depends(get_db)
):
    # 1. 读取上传文件的文本内容
    content = await file.read()
    # 尝试 UTF-8，失败则尝试 GBK，再失败则忽略无法解码的字符
    try:
        raw_text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = content.decode("gbk")
        except UnicodeDecodeError:
            raw_text = content.decode("utf-8", errors="ignore")

    # 2. 创建角色记录，暂存原始文本
    role = Role(
        name=name,
        description=description,
        raw_material=raw_text
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    # 3. 用人设提取Agent生成角色设定指令
    persona = generate_persona_instruction(raw_text)
    role.persona_instruction = persona
    db.commit()
    db.refresh(role)

    return ApiResponse.ok(data={
        "role_id": role.id,
        "name": role.name,
        "persona_instruction": role.persona_instruction
    })

@router.get("/roles/{role_id}")
async def get_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return ApiResponse.ok(data={
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "persona_instruction": role.persona_instruction
    })

@router.post("/roles/{role_id}/build-kb")
async def build_knowledge_base(role_id: int, db: Session = Depends(get_db)):
    """为指定角色构建知识库（分块+向量化）"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if not role.raw_material:
        raise HTTPException(status_code=400, detail="角色没有原始素材，请先上传")

    chunk_count = build_role_knowledge_base(role_id, role.raw_material)
    return ApiResponse.ok(data={
        "role_id": role_id,
        "chunk_count": chunk_count,
        "msg": f"知识库构建完成，共生成 {chunk_count} 个文本块"
    })

# ====== 更新角色 ======
@router.put("/roles/{role_id}")
async def update_role_api(
    role_id: int,
    update_data: RoleUpdate,
    db: Session = Depends(get_db)
): 
    logger.info(f"收到更新角色请求：role_id={role_id}")
    """更新角色信息。提供什么字段就更新什么字段。"""
    role = update_role(role_id, update_data.model_dump(exclude_unset=True), db)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return ApiResponse.ok(data={"id": role.id, "name": role.name, "msg": "角色信息已更新"})


# ====== 删除角色 ======
@router.delete("/roles/{role_id}")
async def delete_role_api(role_id: int, db: Session = Depends(get_db)):
    """删除角色及其关联数据。"""
    logger.info(f"收到删除角色请求：role_id={role_id}")
    role_name = delete_role(role_id, db)
    if not role_name:
        raise HTTPException(status_code=404, detail="角色不存在")
    return ApiResponse.ok(msg=f"角色「{role_name}」已被永久删除")

@router.put("/roles/{role_id}/persona")
async def update_persona_api(
    role_id: int,
    data: PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动编辑角色人设（需要登录）"""
    logger.info(f"用户 {current_user.username} 请求修改角色 {role_id} 人设")
    role = update_persona(role_id, data.persona_instruction, db)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return ApiResponse.ok(data={"role_id": role.id, "msg": "人设已更新"})