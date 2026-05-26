# app/agents/persona_agent.py
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

# 初始化LLM
llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=0.3,
    base_url=settings.OLLAMA_BASE_URL
)

# 人设提取提示词
PERSONA_EXTRACT_PROMPT = ChatPromptTemplate.from_template("""
你是一个专业的角色设定分析师。请根据以下角色对话素材，提炼出该角色的：
1. 性格特点（包括优点和缺点）
2. 说话语气与口头禅
3. 行为逻辑与习惯
4. 兴趣爱好
5. 其他突出的人物设定

请以结构化的方式输出，作为后续角色扮演的系统指令。不要添加任何多余的解释。

角色素材：
{materials}

角色设定指令：
""")

def generate_persona_instruction(materials_text: str) -> str:
    """从角色素材中提取人设指令"""
    chain = PERSONA_EXTRACT_PROMPT | llm | StrOutputParser()
    return chain.invoke({"materials": materials_text})