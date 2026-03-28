#!/usr/bin/env python3
"""
使用微信API配置公众号服务器地址
"""
import requests
import json
import time

APPID = "wx4bf0c5fd794ea6c6"
APPSECRET = "357f4a65a32262dfc4a4395278ad6685"
TOKEN = "taxi_agent_202603272157"
URL = "http://ysywlkj.xyz/wechat/callback"


def get_access_token():
    """获取access_token"""
    api_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
    
    try:
        resp = requests.get(api_url, timeout=10)
        data = resp.json()
        
        if "access_token" in data:
            print(f"✅ 获取access_token成功: {data['access_token'][:20]}...")
            return data["access_token"]
        else:
            print(f"❌ 获取失败: {data}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def set_server_url(access_token):
    """设置服务器地址"""
    api_url = f"https://api.weixin.qq.com/cgi-bin/server/update?access_token={access_token}"
    
    payload = {
        "url": URL,
        "token": TOKEN,
        "encodingaeskey": "",  # 可留空，自动生成
        "callback_func": 1  # 1=明文模式
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        data = resp.json()
        
        print(f"📋 API响应: {json.dumps(data, ensure_ascii=False)}")
        
        if data.get("errcode") == 0:
            print("✅ 服务器地址设置成功!")
            return True
        else:
            print(f"❌ 设置失败: errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def main():
    print("=" * 50)
    print("🚗 Taxi Agent - 微信服务器配置")
    print("=" * 50)
    print(f"配置URL: {URL}")
    print(f"Token: {TOKEN}")
    print()
    
    # 获取access_token
    access_token = get_access_token()
    if not access_token:
        print("\n❌ 无法获取access_token，请检查AppID和AppSecret")
        return
    
    print()
    
    # 设置服务器地址
    if set_server_url(access_token):
        print("\n🎉 微信服务器配置完成!")
    else:
        print("\n⚠️ 配置失败，请手动在微信公众号后台配置")


if __name__ == "__main__":
    main()
