from collections import defaultdict
from app.core.logger import logger

# 内存存储：{(user_id, role_id): [{"role": "user/ai", "content": "..."}, ...]}
_sessions: dict[tuple[int, int], list[dict]] = defaultdict(list)
MAX_HISTORY_MESSAGES = 20

def add_message(user_id: int, role_id: int, role: str, content: str):
    """向会话历史中添加一条消息，自动截断"""
    key = (user_id, role_id)
    _sessions[key].append({"role": role, "content": content})
    if len(_sessions[key]) > MAX_HISTORY_MESSAGES:
        _sessions[key] = _sessions[key][-MAX_HISTORY_MESSAGES:]
        logger.debug(f"会话历史已截断，用户={user_id}，角色={role_id}")

def get_history(user_id: int, role_id: int) -> list[dict]:
    """获取指定用户与角色的对话历史"""
    key = (user_id, role_id)
    return _sessions[key].copy()

def clear_history(user_id: int, role_id: int):
    """清除指定用户与角色的对话历史"""
    key = (user_id, role_id)
    _sessions[key].clear()
    logger.info(f"已清除会话历史，用户={user_id}，角色={role_id}")