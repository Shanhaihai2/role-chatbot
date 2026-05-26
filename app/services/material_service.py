from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

# 全局单例 Embedding 模型
embeddings = HuggingFaceEmbeddings(
    model_name=settings.EMBEDDING_MODEL_PATH,
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

def chunk_text(text: str, chunk_size=500, chunk_overlap=50) -> List[str]:
    """将长文本分割为适合检索的块"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    # split_text 返回纯字符串列表
    chunks = splitter.split_text(text)
    return chunks

def build_role_knowledge_base(role_id: int, raw_text: str) -> int:
    """
    将角色原始素材分块、向量化，存入 Chroma
    返回文本块数量
    """
    # 1. 分块
    chunks = chunk_text(raw_text)
    if not chunks:
        raise ValueError("素材无有效文本")

    # 2. 转换为 LangChain Document 对象，并附加角色ID元数据
    from langchain_core.documents import Document
    docs = [
        Document(page_content=chunk, metadata={"role_id": str(role_id)})
        for chunk in chunks
    ]

    # 3. 存入 Chroma（每个角色使用独立的 collection）
    collection_name = f"role_{role_id}"
    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
        collection_name=collection_name,
    )
    return len(chunks)