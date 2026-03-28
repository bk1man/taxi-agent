"""
高德地图服务
"""
import requests
import json

AMAP_KEY = "b8eac5f9a5f48ebb1ce317c4216ff066"
AMAP_API = "https://restapi.amap.com/v3"


def geocode(address: str) -> dict:
    """
    地址转坐标
    返回: {"lat": float, "lng": float, "address": str}
    """
    url = f"{AMAP_API}/geocode/geo"
    params = {
        "key": AMAP_KEY,
        "address": address,
        "output": "json"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if data.get("status") == "1" and data.get("geocodes"):
            g = data["geocodes"][0]
            return {
                "lat": float(g["location"].split(",")[1]),
                "lng": float(g["location"].split(",")[0]),
                "address": g.get("formatted_address", address),
                "province": g.get("province", ""),
                "city": g.get("city", ""),
                "district": g.get("district", "")
            }
        else:
            return None
    except Exception as e:
        print(f"[Map] Geocode error: {e}")
        return None


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    坐标转地址
    """
    url = f"{AMAP_API}/geocode/regeo"
    params = {
        "key": AMAP_KEY,
        "location": f"{lng},{lat}",
        "output": "json"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if data.get("status") == "1":
            r = data.get("regeocode", {})
            a = r.get("addressComponent", {})
            return {
                "address": r.get("formatted_address", ""),
                "province": a.get("province", ""),
                "city": a.get("city", ""),
                "district": a.get("district", ""),
                "street": a.get("streetNumber", {}).get("street", "")
            }
        return None
    except Exception as e:
        print(f"[Map] Reverse geocode error: {e}")
        return None


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
    """
    计算两点间距离和预计行驶时间
    """
    url = f"{AMAP_API}/direction/driving"
    params = {
        "key": AMAP_KEY,
        "origin": f"{lng1},{lat1}",
        "destination": f"{lng2},{lat2}",
        "output": "json"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if data.get("status") == "1":
            route = data.get("route", {})
            paths = route.get("paths", [])
            if paths:
                p = paths[0]
                return {
                    "distance_km": round(int(p.get("distance", 0)) / 1000, 1),
                    "duration_minutes": round(int(p.get("duration", 0)) / 60)
                }
        
        # 如果API失败，使用简单计算
        return simple_distance(lat1, lng1, lat2, lng2)
        
    except Exception as e:
        print(f"[Map] Calculate distance error: {e}")
        return simple_distance(lat1, lng1, lat2, lng2)


def simple_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
    """简单的直线距离计算"""
    import math
    
    R = 6371  # 地球半径km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    
    # 直线距离乘1.4作为道路估算距离
    road_distance = distance * 1.4
    # 假设平均速度30km/h
    duration = int(road_distance / 30 * 60)
    
    return {
        "distance_km": round(road_distance, 1),
        "duration_minutes": max(1, duration)
    }


def search_nearby(lat: float, lng: float, keywords: str = "酒店", radius: int = 1000) -> list:
    """
    搜索附近地点
    """
    url = f"{AMAP_API}/place/around"
    params = {
        "key": AMAP_KEY,
        "location": f"{lng},{lat}",
        "keywords": keywords,
        "radius": radius,
        "output": "json"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if data.get("status") == "1":
            pois = data.get("pois", [])
            return [{
                "name": p.get("name", ""),
                "address": p.get("address", ""),
                "lat": float(p.get("location", "0,0").split(",")[1]),
                "lng": float(p.get("location", "0,0").split(",")[0]),
                "distance": int(p.get("distance", 0))
            } for p in pois]
        return []
    except Exception as e:
        print(f"[Map] Search nearby error: {e}")
        return []


if __name__ == "__main__":
    # 测试
    print("=== 高德地图 API 测试 ===")
    
    # 测试地址解析
    result = geocode("北京市朝阳区望京SOHO")
    print(f"望京SOHO: {result}")
    
    # 测试距离计算
    result = calculate_distance(39.908, 116.397, 39.985, 116.312)
    print(f"国贸到中关村: {result}")
