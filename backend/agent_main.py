"""
Taxi Agent MVP - Agent 主逻辑
"""
import re
from agent_tools import (
    get_nearby_drivers,
    create_taxi_order,
    assign_driver_to_order,
    get_order_status,
    parse_destination
)

# 乘客会话状态
passenger_sessions = {}


class PassengerSession:
    """乘客会话状态"""
    
    def __init__(self, openid: str):
        self.openid = openid
        self.state = "idle"  # idle -> pickup_known -> destination_known -> ordering -> matched
        self.pickup_address = None
        self.pickup_location = None
        self.destination_address = None
        self.destination_location = None
        self.current_order_no = None
        self.last_drivers = []
    
    def reset(self):
        """重置会话"""
        self.state = "idle"
        self.pickup_address = None
        self.pickup_location = None
        self.destination_address = None
        self.destination_location = None
        self.current_order_no = None
        self.last_drivers = []


def get_session(openid: str) -> PassengerSession:
    """获取或创建会话"""
    if openid not in passenger_sessions:
        passenger_sessions[openid] = PassengerSession(openid)
    return passenger_sessions[openid]


def process_message(openid: str, message: str) -> str:
    """
    处理乘客消息，返回回复文本
    """
    session = get_session(openid)
    message = message.strip()
    
    # 命令处理
    if message in ["打车", "我要打车", "叫车", "出发"]:
        return handle_booking_start(session)
    
    if message in ["取消", "取消订单"]:
        return handle_cancel(session)
    
    if message.startswith("订单") or message.startswith("查订单"):
        order_no = session.current_order_no
        if order_no:
            return handle_query_order(order_no)
        else:
            return "您没有进行中的订单"
    
    # 状态机处理
    if session.state == "idle":
        return handle_idle(session, message)
    
    elif session.state == "pickup_known":
        return handle_pickup_known(session, message)
    
    elif session.state == "destination_known":
        return handle_destination_known(session, message)
    
    elif session.state == "ordering":
        return handle_ordering(session, message)
    
    elif session.state == "matched":
        return handle_matched(session, message)
    
    else:
        session.reset()
        return "好的，已为您重置。请问您要去哪里？"


def handle_booking_start(session: PassengerSession) -> str:
    """开始打车"""
    session.reset()
    session.state = "idle"
    
    # 先尝试获取乘客位置（这里简化处理）
    session.state = "pickup_known"
    session.pickup_address = "我的当前位置"
    session.pickup_location = {"lat": 39.908, "lng": 116.397}
    
    return "好的，我来帮您打车！请问您要去哪里？（可以说目的地名称，如'中关村'、'望京'等）"


def handle_idle(session: PassengerSession, message: str) -> str:
    """空闲状态 - 等待目的地"""
    # 尝试解析目的地
    dest = parse_destination(message)
    if dest:
        session.destination_address = dest['address']
        session.destination_location = {"lat": dest['lat'], "lng": dest['lng']}
        session.state = "destination_known"
        return handle_destination_known(session, message)
    
    # 无法解析，询问具体地址
    return "抱歉，我不太确定您要去哪里。请告诉我具体的目的地，比如：中关村、望京、国贸等"


def handle_pickup_known(session: PassengerSession, message: str) -> str:
    """已知道出发地，等待目的地"""
    dest = parse_destination(message)
    if dest:
        session.destination_address = dest['address']
        session.destination_location = {"lat": dest['lat'], "lng": dest['lng']}
        session.state = "destination_known"
        return handle_destination_known(session, message)
    
    return "请问您要去哪里？"


def handle_destination_known(session: PassengerSession, message: str) -> str:
    """已知道目的地，搜索附近车辆"""
    # 查询附近司机
    result = get_nearby_drivers(
        lat=session.pickup_location.get("lat") if session.pickup_location else None,
        lng=session.pickup_location.get("lng") if session.pickup_location else None
    )
    
    if not result.get("success"):
        return result.get("message", "查询附近车辆失败")
    
    drivers = result.get("drivers", [])
    if not drivers:
        return "抱歉，附近暂无可用车辆，请稍后再试。"
    
    session.last_drivers = drivers
    session.state = "ordering"
    
    return result.get("message", "")


def handle_ordering(session: PassengerSession, message: str) -> str:
    """选车中状态"""
    # 检查是否选择了车辆 - 更宽松的匹配
    match = re.search(r"(?:第?\s*([1-5])\s*号|选择\s*([1-5一ニ三四五])\s*(?:号|))", message)
    if match:
        # group(1) or group(2) has the digit
        digit = match.group(1) or match.group(2)
        idx = int(digit) - 1
        if 0 <= idx < len(session.last_drivers):
            driver = session.last_drivers[idx]
            # 创建订单
            result = create_taxi_order(
                openid=session.openid,
                pickup_address=session.pickup_address or "当前位置",
                destination_address=session.destination_address,
                pickup_lat=session.pickup_location.get("lat") if session.pickup_location else None,
                pickup_lng=session.pickup_location.get("lng") if session.pickup_location else None,
                dest_lat=session.destination_location.get("lat") if session.destination_location else None,
                dest_lng=session.destination_location.get("lng") if session.destination_location else None
            )
            if not result.get("success"):
                return result.get("message", "创建订单失败")
            
            session.current_order_no = result.get("order_no")
            order_msg = result.get("message", "")
            
            # 自动分配司机
            assign_result = assign_driver_to_order(session.current_order_no)
            if assign_result.get("success"):
                session.state = "matched"
                return order_msg + "\n\n" + assign_result.get("message", "")
            else:
                session.state = "matched"
                return order_msg + "\n\n" + "正在为您分配司机，请稍候..."
    
    if "最快的" in message or "最近的" in message or "选1" in message:
        if session.last_drivers:
            driver = session.last_drivers[0]
            session.state = "matched"
            return f"已为您选择最近的 {driver['name']} 师傅，正在创建订单..."
    
    if "重新搜索" in message or "再看看" in message:
        return handle_destination_known(session, message)
    
    # 创建订单
    result = create_taxi_order(
        openid=session.openid,
        pickup_address=session.pickup_address or "当前位置",
        destination_address=session.destination_address,
        pickup_lat=session.pickup_location.get("lat") if session.pickup_location else None,
        pickup_lng=session.pickup_location.get("lng") if session.pickup_location else None,
        dest_lat=session.destination_location.get("lat") if session.destination_location else None,
        dest_lng=session.destination_location.get("lng") if session.destination_location else None
    )
    
    if not result.get("success"):
        return result.get("message", "创建订单失败")
    
    session.current_order_no = result.get("order_no")
    order_msg = result.get("message", "")
    
    # 自动分配司机
    assign_result = assign_driver_to_order(session.current_order_no)
    
    if assign_result.get("success"):
        session.state = "matched"
        return order_msg + "\n\n" + assign_result.get("message", "")
    else:
        return order_msg + "\n\n" + "正在为您分配司机，请稍候..."


def handle_matched(session: PassengerSession, message: str) -> str:
    """已匹配司机状态"""
    if "取消" in message:
        return handle_cancel(session)
    
    if "订单" in message:
        return handle_query_order(session.current_order_no)
    
    if "已完成支付" in message or "支付完成" in message:
        # 更新订单状态为已支付
        try:
            import requests
            resp = requests.post(f"http://localhost:5000/api/order/{session.current_order_no}/pay", timeout=5)
        except:
            pass
        session.reset()
        return "✅ 支付成功！\n\n感谢您的使用，祝您旅途愉快！\n\n如需再次打车，请说'我要打车'"
    
    if "支付" in message or "付款" in message or "二维码" in message:
        return handle_pay(session)
    
    # 行程结束，询问是否支付
    return "您的订单正在处理中，司机即将到达。请在大厅门口等候。如需取消请说'取消订单'"

def handle_pay(session: PassengerSession) -> str:
    """处理支付"""
    if not session.current_order_no:
        return "您没有进行中的订单"
    
    try:
        import requests
        resp = requests.get(f"http://localhost:5000/pay/{session.current_order_no}", timeout=5)
        data = resp.json()
        if data.get('code') == 0:
            code_url = data['data'].get('code_url', '')
            # 生成二维码
            import qrcode
            import io
            import base64
            img = qrcode.make(code_url)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            img_bytes = buf.getvalue()
            
            # 保存临时文件
            import time
            tmp_file = f"/tmp/qr_{session.current_order_no}_{int(time.time())}.png"
            with open(tmp_file, 'wb') as f:
                f.write(img_bytes)
            
            # 上传并发送图片
            from wechat_callback import upload_image_and_send
            upload_image_and_send(session.openid, tmp_file)
            
            return f"您的支付二维码已发送，请扫码支付\n\n支付完成后请说'已完成支付'"
        else:
            return f"支付码获取失败：{data.get('message', '未知错误')}"
    except Exception as e:
        return f"服务暂时不可用：{str(e)}"


def handle_cancel(session: PassengerSession) -> str:
    """取消订单"""
    if session.current_order_no:
        # 这里应该调用取消订单API
        session.reset()
        return "已为您取消订单。如需重新打车，请说'我要打车'"
    
    session.reset()
    return "您没有进行中的订单"


def handle_query_order(order_no: str) -> str:
    """查询订单状态"""
    if not order_no:
        return "没有找到订单信息"
    
    result = get_order_status(order_no)
    
    if result.get("success"):
        return result.get("message", "")
    else:
        return result.get("message", "查询失败")


# Prompt 模板
TAXI_AGENT_PROMPT = """
你是滴滴打车的智能助手，帮助用户快速叫车。

## 核心功能
1. 接收用户打车请求
2. 理解出发地和目的地
3. 查询附近可用车辆
4. 创建订单并分配司机
5. 提供订单状态查询

## 对话流程
用户说"我要打车" → 询问目的地 → 查询车辆 → 用户选择 → 创建订单 → 分配司机 → 告知司机信息

## 常用话术
- 开始打车："好的，我来帮您打车！请问您要去哪里？"
- 查询车辆："为您查询附近车辆..."
- 选车："附近有X辆可用车辆：1. 张师傅 | 宝马 | 距您0.8km..."
- 创建订单："正在为您创建订单..."
- 分配成功："已为您匹配到张师傅，车牌京A12345，预计3分钟到达"

## 注意事项
- 保持简洁，每条消息不超过100字
- 使用中文友好表达
- 遇到问题请说"抱歉，遇到了点问题，请稍后再试"
"""


if __name__ == "__main__":
    # 测试对话
    session = PassengerSession("test_openid")
    
    print("=== 打车流程测试 ===\n")
    
    print("用户: 我要打车")
    print(f"助手: {process_message('test_openid', '我要打车')}\n")
    
    print("用户: 去中关村")
    print(f"助手: {process_message('test_openid', '去中关村')}\n")
    
    print("用户: 选择第1号")
    print(f"助手: {process_message('test_openid', '选择第1号')}\n")
    
    print("用户: 查订单")
    print(f"助手: {process_message('test_openid', '查订单')}\n")
