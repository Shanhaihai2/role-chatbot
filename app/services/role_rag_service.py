from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

# 复用全局 Embedding 模型
embeddings = HuggingFaceEmbeddings(
    model_name=settings.EMBEDDING_MODEL_PATH,
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

def retrieve_role_context(role_id: int, query: str, k: int = 3) -> List[str]:
    """
    从角色知识库中检索与问题最相关的对话片段
    返回文本内容列表
    """
    collection_name = f"role_{role_id}"
    vectordb = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )

    docs = vectordb.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]