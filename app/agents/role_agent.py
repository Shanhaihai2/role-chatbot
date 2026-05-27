from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.services.role_rag_service import retrieve_role_context

# 初始化LLM
llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=0.7,  # 角色扮演需要一定的创造性
    base_url=settings.OLLAMA_BASE_URL
)

# 定义Agent状态
class RoleAgentState(TypedDict):
    role_id: int
    role_name: str
    persona: str
    user_message: str
    history: List[str]           # 简化处理：存最近几轮的文本
    retrieved_materials: str     # RAG检索到的素材
    final_response: str

# 节点1：加载角色设定
def load_persona(state: RoleAgentState) -> RoleAgentState:
    """从数据库中加载角色人设，这里简化为从state中读取（由上游传入）"""
    # persona 由调用方在invoke时传入
    return state

# 节点2：检索相关素材
def retrieve_materials(state: RoleAgentState) -> RoleAgentState:
    """调用RAG服务检索角色知识库"""
    docs = retrieve_role_context(
        role_id=state["role_id"],
        query=state["user_message"],
        k=3
    )
    state["retrieved_materials"] = "\n".join(docs)
    return state

# 节点3+4：构建Prompt并生成回复
def generate_response(state: RoleAgentState) -> RoleAgentState:
    """结合人设、素材、对话历史，生成角色回复"""
    # 构建对话历史文本
    history_text = "\n".join(state["history"][-6:]) if state["history"] else "无"

    prompt = ChatPromptTemplate.from_template("""
你是一个角色扮演AI，你必须严格遵守以下角色设定来回答问题。

## 角色设定
{persona}

## 角色过往对话素材（参考风格）
{materials}

## 近期对话历史
{history}

## 当前用户消息
{message}

请完全以角色的身份和语气回复，不要说任何额外的话，不要跳出角色。
回复：""")

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "persona": state["persona"],
        "materials": state["retrieved_materials"],
        "history": history_text,
        "message": state["user_message"]
    })
    state["final_response"] = response
    return state

# 构建图
def build_role_agent():
    graph = StateGraph(RoleAgentState)

    # 添加节点
    graph.add_node("load_persona", load_persona)
    graph.add_node("retrieve_materials", retrieve_materials)
    graph.add_node("generate_response", generate_response)

    # 设置边
    graph.set_entry_point("load_persona")
    graph.add_edge("load_persona", "retrieve_materials")
    graph.add_edge("retrieve_materials", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()

# 全局单例Agent
role_agent = build_role_agent()