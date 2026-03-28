"""
Taxi Agent MVP - Flask 后端服务
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

from models import init_db, Driver, Passenger, Order, calculate_fare
from map_service import calculate_distance

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ========== 乘客端 API ==========


@app.route('/test_route')
def test_route():
    return "TEST OK"

@app.route('/api/passenger/info', methods=['GET'])
def get_passenger_info():
    """获取乘客信息"""
    openid = request.args.get('openid')
    if not openid:
        return jsonify({"code": 400, "message": "缺少openid参数"})
    
    passenger = Passenger.get_or_create(openid)
    return jsonify({"code": 0, "data": passenger})


@app.route('/api/driver/nearby', methods=['GET'])
def get_nearby_drivers():
    """获取附近司机"""
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    limit = request.args.get('limit', default=5, type=int)
    
    if not lat or not lng:
        # 默认位置（北京市朝阳区）
        lat = 39.908
        lng = 116.397
    
    drivers = Driver.get_all_online()
    
    # 计算距离并排序
    for d in drivers:
        if d['latitude'] and d['longitude']:
            dist_result = calculate_distance(lat, lng, d['latitude'], d['longitude']); d['distance_km'] = round(dist_result.get('distance_km', 0) if isinstance(dist_result, dict) else dist_result, 1)
        else:
            d['distance_km'] = 99
    
    # 按距离排序
    drivers = sorted(drivers, key=lambda x: x['distance_km'])[:limit]
    
    # 简化返回数据
    result = []
    for d in drivers:
        result.append({
            "driver_id": d['id'],
            "name": d['name'],
            "phone": d['phone'][:3] + '****' + d['phone'][-4:],
            "car_model": d['car_model'],
            "car_number": d['car_number'],
            "car_color": d['car_color'],
            "distance_km": d['distance_km'],
            "rating": d['rating'],
            "total_orders": d['total_orders']
        })
    
    return jsonify({
        "code": 0,
        "data": {
            "count": len(result),
            "drivers": result
        }
    })


@app.route('/api/order/create', methods=['POST'])
def create_order():
    """创建订单"""
    data = request.get_json()
    
    openid = data.get('openid')
    pickup_address = data.get('pickup_address')
    pickup_lat = data.get('pickup_lat')
    pickup_lng = data.get('pickup_lng')
    destination_address = data.get('destination_address')
    destination_lat = data.get('destination_lat')
    destination_lng = data.get('destination_lng')
    
    if not all([openid, pickup_address, destination_address]):
        return jsonify({"code": 400, "message": "参数不完整"})
    
    # 获取或创建乘客
    passenger = Passenger.get_or_create(openid)
    
    # 计算距离和预估费用
    distance = calculate_distance(
        pickup_lat or 39.908, pickup_lng or 116.397,
        destination_lat or 39.990, destination_lng or 116.312
    )
    fare = calculate_fare(distance.get("distance_km", 0) if isinstance(distance, dict) else distance)
    
    # 创建订单
    order = Order.create(
        passenger_id=passenger['id'],
        pickup_address=pickup_address,
        pickup_lat=pickup_lat or 39.908,
        pickup_lng=pickup_lng or 116.397,
        destination_address=destination_address,
        destination_lat=destination_lat or 39.990,
        destination_lng=destination_lng or 116.312,
        distance_km=round(distance.get("distance_km", 0) if isinstance(distance, dict) else distance, 1),
        estimated_fare=fare
    )
    
    return jsonify({
        "code": 0,
        "message": "订单创建成功",
        "data": {
            "order_no": order['order_no'],
            "distance_km": round(distance.get("distance_km", 0) if isinstance(distance, dict) else distance, 1),
            "estimated_fare": fare
        }
    })


@app.route('/api/order/<order_no>', methods=['GET'])
def get_order(order_no):
    """查询订单状态"""
    order = Order.get_by_no(order_no)
    
    if not order:
        return jsonify({"code": 404, "message": "订单不存在"})
    
    # 格式化返回
    result = {
        "order_no": order['order_no'],
        "status": order['status'],
        "pickup_address": order['pickup_address'],
        "destination_address": order['destination_address'],
        "distance_km": order['distance_km'],
        "estimated_fare": order['estimated_fare'],
        "actual_fare": order['actual_fare'],
        "payment_status": order['payment_status'],
        "created_at": order['created_at']
    }
    
    if order['driver_id']:
        result["driver"] = {
            "name": order.get('driver_name', '司机'),
            "car_model": order.get('car_model', ''),
            "car_number": order.get('car_number', ''),
            "phone": order.get('driver_phone', '')
        }
    
    return jsonify({"code": 0, "data": result})


@app.route('/api/order/list', methods=['GET'])
def get_order_list():
    """获取订单列表"""
    openid = request.args.get('openid')
    limit = request.args.get('limit', default=10, type=int)
    
    if not openid:
        return jsonify({"code": 400, "message": "缺少openid"})
    
    passenger = Passenger.get_or_create(openid)
    orders = Order.get_by_passenger(passenger['id'], limit)
    
    result = []
    for o in orders:
        result.append({
            "order_no": o['order_no'],
            "status": o['status'],
            "pickup_address": o['pickup_address'],
            "destination_address": o['destination_address'],
            "distance_km": o['distance_km'],
            "actual_fare": o['actual_fare'],
            "created_at": o['created_at']
        })
    
    return jsonify({"code": 0, "data": result})


# ========== 司机端 API ==========

@app.route('/api/driver/login', methods=['POST'])
def driver_login():
    """司机登录"""
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone:
        return jsonify({"code": 400, "message": "请提供手机号"})
    
    conn = __import__('models').get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drivers WHERE phone = ?", (phone,))
    driver = cursor.fetchone()
    conn.close()
    
    if not driver:
        return jsonify({"code": 404, "message": "司机不存在"})
    
    return jsonify({
        "code": 0,
        "data": {
            "driver_id": driver['id'],
            "name": driver['name'],
            "phone": driver['phone'],
            "car_model": driver['car_model'],
            "car_number": driver['car_number'],
            "status": driver['status']
        }
    })


@app.route('/api/driver/status', methods=['POST'])
def update_driver_status():
    """更新司机状态"""
    data = request.get_json()
    driver_id = data.get('driver_id')
    status = data.get('status')  # online, offline, busy
    
    if not driver_id or not status:
        return jsonify({"code": 400, "message": "参数不完整"})
    
    Driver.update_status(driver_id, status)
    return jsonify({"code": 0, "message": "状态更新成功"})


@app.route('/api/driver/location', methods=['POST'])
def update_driver_location():
    """更新司机位置"""
    data = request.get_json()
    driver_id = data.get('driver_id')
    lat = data.get('latitude')
    lng = data.get('longitude')
    
    if not all([driver_id, lat, lng]):
        return jsonify({"code": 400, "message": "参数不完整"})
    
    Driver.update_location(driver_id, lat, lng)
    return jsonify({"code": 0, "message": "位置更新成功"})


@app.route('/api/driver/order/accept', methods=['POST'])
def accept_order():
    """司机接单"""
    data = request.get_json()
    driver_id = data.get('driver_id')
    order_no = data.get('order_no')
    
    if not all([driver_id, order_no]):
        return jsonify({"code": 400, "message": "参数不完整"})
    
    order = Order.get_by_no(order_no)
    if not order:
        return jsonify({"code": 404, "message": "订单不存在"})
    
    if order['status'] != 'pending':
        return jsonify({"code": 400, "message": "订单已被其他司机接走"})
    
    Order.assign_driver(order_no, driver_id)
    
    return jsonify({
        "code": 0,
        "message": "接单成功",
        "data": {
            "order_no": order_no,
            "status": "matched",
            "pickup_address": order['pickup_address'],
            "destination_address": order['destination_address']
        }
    })


@app.route('/api/driver/order/complete', methods=['POST'])
def complete_order():
    """完成行程"""
    data = request.get_json()
    order_no = data.get('order_no')
    actual_fare = data.get('actual_fare')
    
    if not all([order_no, actual_fare]):
        return jsonify({"code": 400, "message": "参数不完整"})
    
    Order.complete(order_no, actual_fare)
    return jsonify({"code": 0, "message": "行程已完成"})


# ========== 模拟订单 API（用于测试）============

@app.route('/api/mock/assign_driver', methods=['POST'])
def mock_assign_driver():
    """模拟自动分配司机"""
    data = request.get_json()
    order_no = data.get('order_no')
    
    if not order_no:
        return jsonify({"code": 400, "message": "缺少订单号"})
    
    order = Order.get_by_no(order_no)
    if not order:
        return jsonify({"code": 404, "message": "订单不存在"})
    
    # 获取最近的司机
    drivers = Driver.get_all_online()
    if not drivers:
        return jsonify({"code": 400, "message": "暂无在线司机"})
    
    # 选择第一个在线司机（简化逻辑）
    driver = drivers[0]
    Order.assign_driver(order_no, driver['id'])
    
    return jsonify({
        "code": 0,
        "message": "已分配司机",
        "data": {
            "driver_name": driver['name'],
            "driver_phone": driver['phone'],
            "car_model": driver['car_model'],
            "car_number": driver['car_number']
        }
    })


# ========== 健康检查 ==========

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "taxi-agent-mvp"})


@app.route('/', methods=['GET'])
def index():
    return "🚗 Taxi Agent MVP Backend is running!"


# 注册微信路由
from wechat_callback import register_wechat_routes
register_wechat_routes(app)


if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动服务
    print("🚀 Taxi Agent MVP 服务启动中...")
    print("📍 端口: 5000")
    print("📍 公众号回调: http://你的服务器IP/wechat/callback")
    app.run(host='0.0.0.0', port=5000, debug=False)


@app.route('/wechat/pay_notify', methods=['POST'])
def pay_notify():
    """微信支付回调"""
    from services.pay_service import parse_xml
    import xml.etree.ElementTree as ET
    
    data = request.data
    
    # 解析XML
    try:
        root = ET.fromstring(data)
        return_code = root.find('return_code').text
        if return_code == 'SUCCESS':
            # 支付成功，处理订单
            # 这里简化处理，实际应该验证签名
            return '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'
    except Exception as e:
        pass
    
    return '<xml><return_code><![CDATA[FAIL]]></return_code></xml>'

@app.route("/pay/<order_no>", methods=["GET"])
def get_pay_qrcode(order_no):
    print(f"DEBUG: get_pay_qrcode called with {order_no}")
    """获取支付二维码"""
    order = Order.get_by_no(order_no)
    if not order:
        return jsonify({'code': 1, 'message': '订单不存在'})
    
    if order['payment_status'] == 'paid':
        return jsonify({'code': 0, 'data': {'status': 'already_paid'}})
    
    # 调用微信支付
    from services.pay_service import unified_order
    
    total_fee = int(order['estimated_fare'] * 100)  # 转换为分
    
    result = unified_order(
        out_trade_no=order_no,
        total_fee=total_fee,
        body=f"出租车费-{order['destination_address']}",
        notify_url='http://ysywlkj.xyz/wechat/pay_notify'
    )
    
    if result['success']:
        return jsonify({
            'code': 0,
            'data': {
                'code_url': result['code_url'],
                'prepay_id': result['prepay_id']
            }
        })
    else:
        return jsonify({'code': 1, 'message': result.get('err_msg', '支付创建失败')})


