"""
Taxi Agent MVP - 微信公众号回调处理（支持安全模式）
"""
import hashlib
import time
import xml.etree.ElementTree as ET
import base64
import struct
from Crypto.Cipher import AES
from flask import request, Response
import traceback

# 微信公众号配置
WECHAT_TOKEN = "taxi_agent_202603272157"
WECHAT_APPID = "wx4bf0c5fd794ea6c6"
WECHAT_SECRET = "01fc695af6ecc5c47b021c7a59ba9168"
WECHAT_AES_KEY = "e3PV6ZsoGP9i7UXA982jlntLq04ntMiInwdWe9yfTdT"  # 43字符

# Access Token 缓存
_access_token_cache = {"token": None, "expires_at": 0}

def get_access_token():
    """获取微信 access_token"""
    import requests
    
    # 检查缓存
    if _access_token_cache["token"] and time.time() < _access_token_cache["expires_at"]:
        return _access_token_cache["token"]
    
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get("access_token"):
            _access_token_cache["token"] = data["access_token"]
            _access_token_cache["expires_at"] = time.time() + data.get("expires_in", 7200) - 300
            return data["access_token"]
    except Exception as e:
        print(f"get_access_token error: {e}")
    return None


def pkcs7_decode(data: bytes, length: int) -> bytes:
    """PKCS#7 解码"""
    pad_len = length - (len(data) % length)
    return data + bytes([pad_len] * pad_len)


def aes_decrypt(encrypt_str: str) -> str:
    """
    AES 解密微信消息
    返回: 解密后的明文XML字符串
    """
    AES_KEY = base64.b64decode(WECHAT_AES_KEY + "=")
    
    # 解密
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY[:16])
    encrypted_data = base64.b64decode(encrypt_str)
    decrypted = pkcs7_decode(cipher.decrypt(encrypted_data), 32)
    
    # 去掉PKCS#7 padding，返回明文XML
    return decrypted.decode('utf-8').rstrip()


def verify_wechat_server():
    """验证微信服务器"""
    signature = request.args.get('signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    
    if not all([signature, timestamp, nonce]):
        return False
    
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list)
    hash_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
    
    return hash_str == signature


def parse_wechat_xml(xml_data):
    """解析微信XML消息"""
    root = ET.fromstring(xml_data)
    msg_dict = {}
    for child in root:
        msg_dict[child.tag] = child.text
    return msg_dict


def handle_text_message(from_user, to_user, content):
    """处理文本消息"""
    from agent_main import process_message
    
    # 处理消息
    reply_text = process_message(from_user, content)
    
    # 返回XML
    reply_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply_text}]]></Content>
</xml>"""
    return reply_xml


def handle_event_message(from_user, to_user, event):
    """处理事件消息"""
    if event == "subscribe":
        reply_text = """欢迎使用智能打车服务！🚗

发送"我要打车"即可快速叫车

支持功能：
• 语音/文字叫车
• 附近车辆查询
• 实时订单追踪
• 自动支付

请说"我要打车"开始体验！"""
    elif event == "unsubscribe":
        reply_text = "感谢您的使用，期待下次为您服务！"
    else:
        reply_text = "收到，我会尽快处理！"
    
    reply_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply_text}]]></Content>
</xml>"""
    return reply_xml


def wechat_callback():
    """微信回调入口"""
    print(f"[WeChat] Received {request.method} request")
    
    # GET 请求用于验证
    if request.method == 'GET':
        if verify_wechat_server():
            echostr = request.args.get('echostr', '')
            print(f"[WeChat] Verification success, echostr: {echostr[:20]}...")
            return Response(echostr, mimetype='text/plain')
        print("[WeChat] Verification failed")
        return Response("验证失败", mimetype='text/plain')
    
    # POST 请求处理消息
    encrypt_type = request.args.get('encrypt_type', 'raw')
    print(f"[WeChat] POST encrypt_type: {encrypt_type}")
    
    try:
        if encrypt_type == 'aes':
            # 安全模式 - AES加密
            xml_data = request.data
            print(f"[WeChat] Received encrypted XML: {xml_data[:200]}")
            
            root = ET.fromstring(xml_data)
            encrypt_node = root.find('.//Encrypt')
            if encrypt_node is not None:
                encrypt_str = encrypt_node.text
                print(f"[WeChat] Encrypt content: {encrypt_str[:50]}...")
                
                try:
                    # 解密 - 得到明文XML
                    decrypted_xml = aes_decrypt(encrypt_str)
                    print(f"[WeChat] Decrypted XML: {decrypted_xml[:200]}...")
                    
                    # 解析解密后的XML获取FromUserName和Content
                    decrypted_root = ET.fromstring(decrypted_xml)
                    msg_type = decrypted_root.find('.//MsgType').text
                    from_user = decrypted_root.find('.//FromUserName').text
                    to_user = decrypted_root.find('.//ToUserName').text
                    
                    if msg_type == 'text':
                        content = decrypted_root.find('.//Content').text or ''
                        reply_xml = handle_text_message(from_user, to_user, content)
                    elif msg_type == 'voice':
                        content = decrypted_root.find('.//Recognition').text or ''
                        if not content:
                            content = "我没听清，请再说一次"
                        reply_xml = handle_text_message(from_user, to_user, content)
                    elif msg_type == 'event':
                        event = decrypted_root.find('.//Event').text or ''
                        reply_xml = handle_event_message(from_user, to_user, event)
                    else:
                        reply_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[收到，我会尽快处理！]]></Content>
</xml>"""
                    
                    print(f"[WeChat] Reply: {reply_xml[:100]}...")
                    return Response(reply_xml, mimetype='application/xml')
                    
                except Exception as e:
                    print(f"[WeChat] AES decrypt error: {e}")
                    traceback.print_exc()
                    return Response("success", mimetype='text/plain')
        
        # 明文模式或无加密
        xml_data = request.data
        if not xml_data:
            return Response("success", mimetype='text/plain')
        
        msg_dict = parse_wechat_xml(xml_data)
        print(f"[WeChat] Plain XML msg_dict: {msg_dict}")
        
        msg_type = msg_dict.get('MsgType')
        from_user = msg_dict.get('FromUserName')
        to_user = msg_dict.get('ToUserName')
        
        if msg_type == 'text':
            content = msg_dict.get('Content', '')
            reply_xml = handle_text_message(from_user, to_user, content)
        elif msg_type == 'voice':
            content = msg_dict.get('Recognition', '')
            if not content:
                content = "我没听清，请再说一次"
            reply_xml = handle_text_message(from_user, to_user, content)
        elif msg_type == 'event':
            event = msg_dict.get('Event', '')
            reply_xml = handle_event_message(from_user, to_user, event)
        else:
            reply_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[收到，我会尽快处理！]]></Content>
</xml>"""
        
        print(f"[WeChat] Reply: {reply_xml[:100]}...")
        return Response(reply_xml, mimetype='application/xml')
        
    except Exception as e:
        print(f"[WeChat] 处理消息异常: {e}")
        traceback.print_exc()
        return Response("success", mimetype='text/plain')


# 添加到 Flask app 的路由
def register_wechat_routes(app):
    """注册微信路由"""
    from flask import Blueprint
    
    wechat_bp = Blueprint('wechat', __name__)
    
    @wechat_bp.route('/wechat/callback', methods=['GET', 'POST'])
    def callback():
        return wechat_callback()
    
    app.register_blueprint(wechat_bp)
    
    return wechat_bp


def send_image_message(openid, media_id):
    """发送图片消息"""
    import requests
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={get_access_token()}"
    data = {
        "touser": openid,
        "msgtype": "image",
        "image": {"media_id": media_id}
    }
    requests.post(url, json=data)


def upload_image(file_path):
    """上传图片到微信服务器"""
    import requests
    access_token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image"
    with open(file_path, 'rb') as f:
        files = {'media': f}
        resp = requests.post(url, files=files)
    result = resp.json()
    if result.get('media_id'):
        return result['media_id']
    return None


def upload_image_and_send(openid, file_path):
    """上传图片并发送"""
    import requests
    import json
    
    access_token = get_access_token()
    if not access_token:
        return False
    
    # 上传图片
    url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image"
    with open(file_path, 'rb') as f:
        files = {'media': f}
        resp = requests.post(url, files=files)
    
    result = resp.json()
    media_id = result.get('media_id')
    
    if not media_id:
        return False
    
    # 发送图片消息
    send_url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
    data = {
        "touser": openid,
        "msgtype": "image",
        "image": {"media_id": media_id}
    }
    
    try:
        requests.post(send_url, json=data)
        return True
    except:
        return False
