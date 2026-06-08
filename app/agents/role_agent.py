from typing import TypedDict, List, Annotated
import operator
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.services.role_rag_service import retrieve_role_context
from app.services.memory_service import retrieve_long_term_memories, extract_memory_content, save_long_term_memory
from app.services.security_service import contains_blocked_keywords, semantic_audit
from app.core.logger import logger
from app.utils.datetime_utils import get_current_datetime_info, is_sleeping

# 初始化LLM
llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=0.7,  # 角色扮演需要一定的创造性
    base_url=settings.OLLAMA_BASE_URL,
    streaming=True,
)

# 定义Agent状态
class RoleAgentState(TypedDict):
    role_id: Annotated[int, lambda x, y: y]  # 保留最后一次写入的值
    user_id: Annotated[str, lambda x, y: y]
    role_name: Annotated[str, lambda x, y: y]
    persona: Annotated[str, lambda x, y: y]
    user_message: Annotated[str, lambda x, y: y]
    history: Annotated[List[str], lambda x, y: y]
    retrieved_materials: Annotated[str, lambda x, y: y]
    retrieved_memories: Annotated[str, lambda x, y: y]
    final_response: Annotated[str, lambda x, y: y]

# 节点1：加载角色设定
def load_persona(state: RoleAgentState) -> RoleAgentState:
    """从数据库中加载角色人设，这里简化为从state中读取（由上游传入）"""
    # persona 由调用方在invoke时传入
    return state

def retrieve_memories(state: RoleAgentState) -> RoleAgentState:
    """检索长期记忆"""
    docs = retrieve_long_term_memories(
        role_id=state["role_id"],
        user_id=state["user_id"],
        query=state["user_message"],
        k=3
    )
    state["retrieved_memories"] = "\n".join(docs) if docs else "无"
    return state

# 节点2：检索相关素材
def retrieve_materials(state: RoleAgentState) -> RoleAgentState:
    """调用RAG服务检索角色知识库"""
    docs = retrieve_role_context(
        role_id=state["role_id"],
        query=state["user_message"],
        k=5
    )
    # 过滤：只保留目标角色的台词行
    role_name = state["role_name"]
    filtered_materials = []
    for doc in docs:
        lines = doc.split("\n")
        role_lines = [
            line for line in lines
            if line.strip().startswith(f"[{role_name}]") or line.strip().startswith(f"{role_name}：") or line.strip().startswith(f"{role_name}:")
        ]
        if role_lines:
            filtered_materials.extend(role_lines)
    
    # 取前3条
    state["retrieved_materials"] = "\n".join(filtered_materials[:3]) if filtered_materials else "无"
    return state

# 节点3+4：构建Prompt并生成回复
def generate_response(state: RoleAgentState) -> RoleAgentState:
    """结合人设、素材、对话历史，生成角色回复"""
    # 构建对话历史文本
    history_text = "\n".join(state["history"][-6:]) if state["history"] else "无"

    # 获取当前时间信息
    time_info = get_current_datetime_info()
    time_context = f"""现在是{time_info['current_date']} {time_info['weekday']} {time_info['current_time']}（{time_info['time_period']}）。"""

    if time_info['holiday']:
        time_context += f" 今天是{time_info['holiday']}。"

    # 作息判断（使用默认作息表，后续可从数据库读取）
    default_schedule = {"sleep": "23:00-07:00", "work": "09:00-18:00"}
    sleeping = is_sleeping(default_schedule)
    if sleeping:
        time_context += f" 现在是你（{state['role_name']}）的睡觉时间。如果用户在这个时候打扰你，你应该表现出被吵醒的样子，语气慵懒、不耐烦或迷糊，但仍保持角色设定。"
        logger.info(f"角色 {state['role_name']} 处于睡眠时段，回复将带有困倦语气")

    prompt = ChatPromptTemplate.from_template("""
你是一个角色扮演AI，你的身份是{role_name}。你必须完全以{role_name}的身份、语气、性格说话。

{time_context}

## 你的角色设定
{persona}

## 你对眼前这个用户的长期记忆
{memories}

## {role_name}的说话风格参考（只能学语气用词，禁止复述内容）
{materials}

## 近期对话历史
{history}

## 当前用户消息
{message}

---
终极规则（违反一条即失败）：
1. 你的回复必须是全新的，一个完整的句子都不能从素材中直接抄。
2. 素材中其他角色（如"小红"）的台词你一个字都不能说，你不是他们。
3. 如果记忆里有用户的名字，用它称呼用户。如果没有，只能称呼"你"，绝对禁止编造任何名字。
4. 你的回复应该只包含你对当前用户消息的回应，不能自言自语、不能自问自答、不能继续对话素材中的情节。
5. 直接输出回复内容，不要加任何前缀如"{role_name}："。

{role_name}的回复：""")

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "persona": state["persona"],
        "memories": state["retrieved_memories"],
        "materials": state["retrieved_materials"],
        "history": history_text,
        "message": state["user_message"],
        "role_name": state["role_name"],
        "time_context": time_context,
    })
     # 尝试从 LLM 响应中获取 token 信息（仅当 llm 返回 AIMessage 时可获取）
    # StrOutputParser 已经提取了纯文本，丢失了 usage_metadata。这里暂时使用估算方式。
    # 若要精确统计，可改用 chain = prompt | llm，然后手动解析。

    token_estimate = len(response)  # 粗略估算：中文每字约1.5个token
    logger.info(f"角色 {state['role_name']} 生成回复，估算Token消耗：{token_estimate} 字符")

    state["final_response"] = response
    logger.info(f"角色 {state['role_name']} 生成回复完成，长度：{len(response)}")
    return state

def security_check(state: RoleAgentState) -> RoleAgentState:
    """双层风控：关键词 + LLM 语义审核"""
    response = state["final_response"]
    logger.info("开始内容安全审核...")

    # 第一层：关键词过滤
    if contains_blocked_keywords(response):
        logger.warning("内容安全：关键词拦截")
        state["final_response"] = "（系统提示：该回复因内容安全原因已被拦截）"
        return state

    # 第二层：LLM 语义审核
    safe, reason = semantic_audit(response)
    if not safe:
        logger.warning(f"内容安全：语义拦截，原因：{reason}")
        state["final_response"] = f"（系统提示：该回复因内容安全原因已被拦截。原因：{reason}）"

    logger.info("内容安全审核通过")
    return state

def extract_new_memories(state: RoleAgentState) -> RoleAgentState:
    """从本轮对话中提取新的长期记忆（异步保存，不阻塞回复）"""
    conversation = f"用户：{state['user_message']}\n{state['role_name']}：{state['final_response']}"
    info = extract_memory_content(conversation)
    if info.strip() and info.strip() != "无":
        for line in info.strip().split("\n"):
            line = line.strip()
            if line:
                save_long_term_memory(state["role_id"], state["user_id"],line, conversation)
    return state

# 构建图
def build_role_agent():
    graph = StateGraph(RoleAgentState)

    # 添加节点
    graph.add_node("load_persona", load_persona)
    graph.add_node("retrieve_memories", retrieve_memories)       # 新
    graph.add_node("retrieve_materials", retrieve_materials)
    graph.add_node("generate_response", generate_response)
    graph.add_node("security_check", security_check)
    graph.add_node("extract_new_memories", extract_new_memories) # 新

    # 设置边
    graph.set_entry_point("load_persona")
    graph.add_edge("load_persona", "retrieve_memories")
    graph.add_edge("retrieve_memories", "retrieve_materials")
    graph.add_edge("retrieve_materials", "generate_response")
    graph.add_edge("generate_response", "security_check")
    graph.add_edge("generate_response", "extract_new_memories")
    graph.add_edge("extract_new_memories", END)

    return graph.compile()

# 全局单例Agent
role_agent = build_role_agent()