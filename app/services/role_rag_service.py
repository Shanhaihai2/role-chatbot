from typing import List
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
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
    # 1. 语义检索
    vectordb = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )
    semantic_docs = vectordb.similarity_search(query, k=5)

    # 2. 获取所有已存储的文档用于构建 BM25 检索器
    all_docs = vectordb.get()
    if all_docs and all_docs.get("documents"):
        text_list = all_docs["documents"]
        bm25_docs = [Document(page_content=text) for text in text_list]
        bm25_retriever = BM25Retriever.from_documents(bm25_docs)
        bm25_retriever.k = 5
        keyword_docs = bm25_retriever.invoke(query)
    else:
        keyword_docs = []

    # 3. 手动合并去重
    combined = list(semantic_docs)
    for doc in keyword_docs:
        if doc.page_content not in [d.page_content for d in combined]:
            combined.append(doc)
    
    # 4. 返回前 k 条
    return [doc.page_content for doc in combined[:k]]