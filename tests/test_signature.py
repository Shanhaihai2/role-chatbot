# test_signature.py
import hashlib

# 这里就是你在 .env 和微信测试号页面填的 Token，必须完全一致
WECHAT_TOKEN = "mywechattoken123"

# 假设这是微信服务器发来的参数
timestamp = "1234567890"
nonce = "abcdefg"
echostr = "hello_world"

# 这是根据微信官方算法生成的签名
tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
tmp_str = "".join(tmp_list)
correct_signature = hashlib.sha1(tmp_str.encode()).hexdigest()

print(f"请把下面的URL粘贴到浏览器访问：")
print(f"https://durably-buffer-upcountry.ngrok-free.dev/api/v1/wechat?signature={correct_signature}&timestamp={timestamp}&nonce={nonce}&echostr={echostr}")