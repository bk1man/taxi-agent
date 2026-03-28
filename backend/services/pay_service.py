"""
微信支付服务 - APIv2
"""
import hashlib
import time
import random
import string
import requests
from urllib.parse import urlencode

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WECHAT_MCHID, WECHAT_API_KEY, WECHAT_APPID, CERT_PATH, KEY_PATH


def generate_nonce_str(length=32):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def generate_sign(params):
    sorted_params = sorted([(k, v) for k, v in params.items() if k and v], key=lambda x: x[0])
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    sign_str += f"&key={WECHAT_API_KEY}"
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()


def to_xml(params):
    xml_items = ['<xml>']
    for k, v in params.items():
        xml_items.append(f'<{k}><![CDATA[{v}]]></{k}>')
    xml_items.append('</xml>')
    return ''.join(xml_items)


def parse_xml(xml_str):
    import re
    result = {}
    pattern = r'<(\w+)><!\[CDATA\[(.*?)\]\]></\1>'
    for match in re.findall(pattern, xml_str):
        result[match[0]] = match[1]
    pattern2 = r'<(\w+)>([^<]+)</\1>'
    for match in re.findall(pattern2, xml_str):
        if match[0] not in result:
            result[match[0]] = match[1]
    return result


def unified_order(out_trade_no, total_fee, body, notify_url=None):
    """统一下单"""
    url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
    
    params = {
        'appid': WECHAT_APPID,
        'mch_id': WECHAT_MCHID,
        'nonce_str': generate_nonce_str(),
        'body': body,
        'out_trade_no': out_trade_no,
        'total_fee': int(total_fee),
        'spbill_create_ip': '39.102.102.25',
        'notify_url': notify_url or 'http://ysywlkj.xyz/wechat/pay_notify',
        'trade_type': 'NATIVE',
    }
    
    params['sign'] = generate_sign(params)
    xml_data = to_xml(params)
    
    try:
        response = requests.post(url, data=xml_data.encode('utf-8'),
                              headers={'Content-Type': 'text/xml'},
                              cert=(CERT_PATH, KEY_PATH),
                              timeout=10)
        result = parse_xml(response.text)
        
        if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
            return {
                'success': True,
                'code_url': result.get('code_url'),
                'prepay_id': result.get('prepay_id'),
                'out_trade_no': out_trade_no
            }
        else:
            return {
                'success': False,
                'err_code': result.get('err_code', ''),
                'err_msg': result.get('err_msg', result.get('return_msg', ''))
            }
    except Exception as e:
        return {'success': False, 'err_msg': str(e)}


def query_order(out_trade_no):
    """查询订单"""
    url = "https://api.mch.weixin.qq.com/pay/orderquery"
    
    params = {
        'appid': WECHAT_APPID,
        'mch_id': WECHAT_MCHID,
        'out_trade_no': out_trade_no,
        'nonce_str': generate_nonce_str(),
    }
    
    params['sign'] = generate_sign(params)
    xml_data = to_xml(params)
    
    try:
        response = requests.post(url, data=xml_data.encode('utf-8'),
                              headers={'Content-Type': 'text/xml'},
                              cert=(CERT_PATH, KEY_PATH),
                              timeout=10)
        result = parse_xml(response.text)
        
        if result.get('return_code') == 'SUCCESS':
            return {
                'success': True,
                'trade_state': result.get('trade_state', 'UNKNOWN'),
                'trade_state_desc': result.get('trade_state_desc', ''),
            }
        else:
            return {'success': False, 'err_msg': result.get('return_msg', '查询失败')}
    except Exception as e:
        return {'success': False, 'err_msg': str(e)}


if __name__ == '__main__':
    print("测试统一下单...")
    result = unified_order('TEST' + str(int(time.time())), 1, '出租车费用')
    print(result)