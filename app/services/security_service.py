from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.core.logger import logger

# 第一层：关键词黑名单
BLOCKED_KEYWORDS = [
    "赌博", "赌场", "彩票",
    "毒品", "吸毒",
    "枪支", "弹药",
    "色情", "裸体",
    "诈骗", "洗钱",
    "自杀", "自残",
    "暴力", "恐怖",
]

def contains_blocked_keywords(text: str) -> bool:
    """检查文本是否包含违禁关键词，返回 True 表示命中"""
    for kw in BLOCKED_KEYWORDS:
        if kw in text:
            logger.warning(f"内容安全：命中关键词「{kw}」")
            return True
    return False

# 第二层：LLM 语义审核
audit_llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=0,
    base_url=settings.OLLAMA_BASE_URL
)

AUDIT_PROMPT = ChatPromptTemplate.from_template("""
你是一个内容安全审核员。请审查以下AI角色的回复内容是否包含：
- 色情、低俗、性暗示
- 暴力、恐怖、自残
- 违法违规、诈骗
- 政治敏感、分裂国家
- 侮辱、歧视、人身攻击

如果内容安全，回复"安全"；如果包含以上任何问题，回复"违规：<具体原因>"。

待审查内容：
{content}

审核结果：""")

def semantic_audit(content: str) -> tuple:
    """
    LLM 语义审核
    返回 (是否安全, 审核结果)
    """
    try:
        chain = AUDIT_PROMPT | audit_llm | StrOutputParser()
        result = chain.invoke({"content": content})
        logger.info(f"语义审核完成，结果：{result[:50]}...")
        if "安全" in result and "违规" not in result:
            return True, result
        else:
            logger.warning(f"内容安全：语义审核不通过，原因：{result}")
            return False, result
    except Exception as e:
        logger.error(f"语义审核异常：{e}")
        # 审核失败时保守处理：放行，避免影响正常对话
        return True, "审核异常，已放行"