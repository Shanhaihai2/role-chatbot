from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.role import Role
from app.core.response import ApiResponse
from app.agents.persona_agent import generate_persona_instruction
from app.services.material_service import build_role_knowledge_base

router = APIRouter()

@router.post("/roles")
async def create_role(
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),   # 暂时只接受一个文本文件
    db: Session = Depends(get_db)
):
    # 1. 读取上传文件的文本内容
    raw_text = (await file.read()).decode("utf-8")

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

