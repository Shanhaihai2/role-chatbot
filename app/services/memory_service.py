from typing import List
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.memory import LongTermMemory

# 复用全局 Embedding 模型
embeddings = HuggingFaceEmbeddings(
    model_name=settings.EMBEDDING_MODEL_PATH,
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 提取记忆的 LLM
memory_llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=0.3,
    base_url=settings.OLLAMA_BASE_URL
)

def extract_memory_content(conversation: str) -> str:
    """从一段对话中提取值得记住的关键信息"""
    prompt = ChatPromptTemplate.from_template("""
从以下对话中，提取关于用户的关键信息，尤其是：
- 用户的名字（如果用户说"我叫XX"、"我的名字是XX"或者"我是XX"，XX就是名字）
- 用户的喜好、习惯、个人经历、计划等
每条信息一行，格式为"用户的名字是XX"或"用户喜欢XX"。如果对话中确实没有用户相关信息，才输出"无"。

对话：
{conversation}

关键信息：""")

    chain = prompt | memory_llm | StrOutputParser()
    return chain.invoke({"conversation": conversation})

def save_long_term_memory(role_id: int, user_id: str, content: str, source: str):
    """保存长期记忆到数据库和向量库"""
    # 1. 存入 SQLite
    db = SessionLocal()
    memory = LongTermMemory(
        role_id=role_id,
        user_id=user_id,
        content=content,
        source_conversation=source
    )
    db.add(memory)
    db.commit()
    memory_id = memory.id  # 在 close 之前取出 id
    db.close()

    # 2. 存入 Chroma（按角色和用户隔离）
    doc = Document(
        page_content=content,
        metadata={"role_id": str(role_id), "user_id": user_id, "memory_id": str(memory_id)}
    )
    collection_name = f"role_{role_id}_memory_user_{user_id}" 
    Chroma.from_documents(
        documents=[doc],
        embedding=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
        collection_name=collection_name
    )

def retrieve_long_term_memories(role_id: int, user_id: str, query: str, k: int = 3) -> List[str]:
    """检索与当前话题相关的长期记忆"""
    collection_name = f"role_{role_id}_memory_user_{user_id}" 
    try:
        vectordb = Chroma(
           collection_name=collection_name,
         embedding_function=embeddings,
          persist_directory=settings.CHROMA_PERSIST_DIR
        )
        docs = vectordb.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
    except Exception:
        return []