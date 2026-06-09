import hashlib
import requests
from app.core.config import settings
from app.core.logger import logger

def verify_signature(signature: str, timestamp: str, nonce: str) -> bool:
    """
    验证微信服务器发来的签名是否正确。
    这是微信接入验证的关键步骤。
    """
    tmp_list = sorted([settings.WECHAT_TOKEN, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    calculated = hashlib.sha1(tmp_str.encode()).hexdigest()
    return calculated == signature

def get_access_token() -> str:
    """获取微信公众号 access_token，用于后续 API 调用"""
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        token = data.get("access_token")
        if token:
            logger.info("微信 access_token 获取成功")
            return token
        else:
            logger.error(f"获取 access_token 失败：{data}")
            return ""
    except Exception as e:
        logger.error(f"获取 access_token 异常：{e}")
        return ""

def send_custom_message(openid: str, content: str) -> bool:
    """向指定用户发送客服消息"""
    access_token = get_access_token()
    if not access_token:
        return False

    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
    data = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": content}
    }
    try:
        # 关键修复：ensure_ascii=False 保证中文不被转义
        import json
        resp = requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info(f"微信消息发送成功：openid={openid}")
            return True
        else:
            logger.error(f"微信消息发送失败：{result}")
            return False
    except Exception as e:
        logger.error(f"微信消息发送异常：{e}")
        return False
