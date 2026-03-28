"""
Taxi Agent MVP - OpenClaw Agent 工具
"""
import requests
import re
from typing import Optional

# 后端 API 地址
API_BASE = "http://localhost:5000"


def get_nearby_drivers(lat: float = None, lng: float = None, limit: int = 5) -> dict:
    """
    查询附近可用司机
    """
    params = {"lat": lat or 39.908, "lng": lng or 116.397, "limit": limit}
    
    try:
        resp = requests.get(f"{API_BASE}/api/driver/nearby", params=params, timeout=5)
        data = resp.json()
        
        if data.get('code') == 0:
            drivers = data['data']['drivers']
            if not drivers:
                return {
                    "success": True,
                    "message": "附近暂无可用车辆，请稍后再试",
                    "drivers": []
                }
            
            driver_list = "\n".join([
                f"{i+1}. {d['name']} | {d['car_model']} | 距您{d['distance_km']}km | ⭐{d['rating']}"
                for i, d in enumerate(drivers)
            ])
            
            return {
                "success": True,
                "message": f"找到 {len(drivers)} 辆可用车辆：\n{driver_list}\n\n请说'我要打车'或直接说'选择第X号'",
                "drivers": drivers
            }
        else:
            return {"success": False, "message": "查询失败，请重试"}
    
    except Exception as e:
        return {"success": False, "message": f"服务暂时不可用：{str(e)}"}


def create_taxi_order(openid: str, pickup_address: str, destination_address: str,
                      pickup_lat: float = None, pickup_lng: float = None,
                      dest_lat: float = None, dest_lng: float = None) -> dict:
    """
    创建打车订单
    """
    payload = {
        "openid": openid,
        "pickup_address": pickup_address,
        "pickup_lat": pickup_lat or 39.908,
        "pickup_lng": pickup_lng or 116.397,
        "destination_address": destination_address,
        "destination_lat": dest_lat or 39.990,
        "destination_lng": dest_lng or 116.312
    }
    
    try:
        resp = requests.post(f"{API_BASE}/api/order/create", json=payload, timeout=5)
        data = resp.json()
        
        if data.get('code') == 0:
            order_info = data['data']
            return {
                "success": True,
                "message": f"✅ 订单已创建！\n订单号：{order_info['order_no']}\n距离：{order_info['distance_km']}km\n预估费用：{order_info['estimated_fare']}元\n\n正在为您查找附近司机...",
                "order_no": order_info['order_no'],
                "distance_km": order_info['distance_km'],
                "estimated_fare": order_info['estimated_fare']
            }
        else:
            return {"success": False, "message": f"创建订单失败：{data.get('message')}"}
    
    except Exception as e:
        return {"success": False, "message": f"服务暂时不可用：{str(e)}"}


def assign_driver_to_order(order_no: str) -> dict:
    """
    为订单分配司机
    """
    try:
        resp = requests.post(
            f"{API_BASE}/api/mock/assign_driver",
            json={"order_no": order_no},
            timeout=5
        )
        data = resp.json()
        
        if data.get('code') == 0:
            driver = data['data']
            return {
                "success": True,
                "message": f"🚗 已为您匹配到司机：\n司机：{driver['driver_name']}\n车型：{driver['car_model']}\n车牌：{driver['car_number']}\n\n预计3分钟后到达，请在大厅门口等候。",
                "driver": driver
            }
        else:
            return {"success": False, "message": data.get('message', '分配司机失败')}
    
    except Exception as e:
        return {"success": False, "message": f"服务暂时不可用：{str(e)}"}


def get_order_status(order_no: str) -> dict:
    """
    查询订单状态
    """
    try:
        resp = requests.get(f"{API_BASE}/api/order/{order_no}", timeout=5)
        data = resp.json()
        
        if data.get('code') == 0:
            order = data['data']
            status_text = {
                "pending": "等待分配中",
                "matched": "司机已接单",
                "picked": "乘客已上车",
                "completed": "行程已完成",
                "cancelled": "订单已取消"
            }.get(order['status'], order['status'])
            
            msg = f"订单状态：{status_text}\n出发地：{order['pickup_address']}\n目的地：{order['destination_address']}"
            
            if order.get('driver'):
                msg += f"\n司机：{order['driver']['name']}\n车型：{order['driver']['car_model']}\n车牌：{order['driver']['car_number']}"
            
            if order['status'] == 'completed':
                msg += f"\n实付金额：{order['actual_fare']}元"
            
            return {"success": True, "message": msg, "order": order}
        else:
            return {"success": False, "message": "订单不存在"}
    
    except Exception as e:
        return {"success": False, "message": f"服务暂时不可用：{str(e)}"}


def parse_location_with_map(text: str) -> Optional[dict]:
    """
    使用高德地图API解析地址
    """
    try:
        from map_service import geocode
        
        result = geocode(text)
        if result:
            return {
                "lat": result["lat"],
                "lng": result["lng"],
                "address": result.get("address", text)
            }
    except Exception as e:
        print(f"[Map] parse_location error: {e}")
    
    return None


def parse_destination(text: str) -> Optional[dict]:
    """解析目的地"""
    return parse_location_with_map(text)


def parse_pickup(text: str) -> Optional[dict]:
    """解析出发地"""
    return parse_location_with_map(text)
