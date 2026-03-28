"""
Taxi Agent MVP - 数据模型
"""
import sqlite3
from datetime import datetime
from typing import Optional, List
import json

DB_PATH = "/root/projects/taxi-agent/database/taxi.db"


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 司机表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            car_model TEXT,
            car_number TEXT UNIQUE NOT NULL,
            car_color TEXT,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'offline',
            rating REAL DEFAULT 5.0,
            total_orders INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 乘客表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passengers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE NOT NULL,
            nickname TEXT,
            phone TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 订单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            passenger_id INTEGER NOT NULL,
            driver_id INTEGER,
            pickup_address TEXT NOT NULL,
            pickup_lat REAL NOT NULL,
            pickup_lng REAL NOT NULL,
            destination_address TEXT NOT NULL,
            destination_lat REAL NOT NULL,
            destination_lng REAL NOT NULL,
            distance_km REAL,
            estimated_fare REAL,
            actual_fare REAL,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            matched_at DATETIME,
            completed_at DATETIME,
            payment_status TEXT DEFAULT 'unpaid',
            FOREIGN KEY (passenger_id) REFERENCES passengers(id),
            FOREIGN KEY (driver_id) REFERENCES drivers(id)
        )
    """)
    
    # 插入模拟司机数据
    cursor.execute("SELECT COUNT(*) FROM drivers")
    if cursor.fetchone()[0] == 0:
        mock_drivers = [
            ("张师傅", "13800138001", "宝马5系", "京A12345", "黑色", 39.910, 116.400, "online"),
            ("李师傅", "13800138002", "奥迪A6L", "京B67890", "白色", 39.915, 116.405, "online"),
            ("王师傅", "13800138003", "特斯拉Model3", "京C11111", "红色", 39.905, 116.395, "online"),
            ("赵师傅", "13800138004", "奔驰E级", "京D22222", "黑色", 39.920, 116.410, "online"),
            ("钱师傅", "13800138005", "比亚迪汉", "京E33333", "蓝色", 39.908, 116.390, "offline"),
        ]
        cursor.executemany("""
            INSERT INTO drivers (name, phone, car_model, car_number, car_color, latitude, longitude, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, mock_drivers)
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")


def generate_order_no():
    """生成订单号"""
    return f"TX{datetime.now().strftime('%Y%m%d%H%M%S')}"


class Driver:
    """司机模型"""
    
    @staticmethod
    def get_all_online() -> List[dict]:
        """获取所有在线司机"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, phone, car_model, car_number, car_color, 
                   latitude, longitude, status, rating, total_orders
            FROM drivers WHERE status = 'online'
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_id(driver_id: int) -> Optional[dict]:
        """根据ID获取司机"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def update_location(driver_id: int, lat: float, lng: float):
        """更新位置"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE drivers SET latitude = ?, longitude = ? WHERE id = ?
        """, (lat, lng, driver_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_status(driver_id: int, status: str):
        """更新状态"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE drivers SET status = ? WHERE id = ?", (status, driver_id))
        conn.commit()
        conn.close()


class Passenger:
    """乘客模型"""
    
    @staticmethod
    def get_or_create(openid: str, nickname: str = None) -> dict:
        """获取或创建乘客"""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM passengers WHERE openid = ?", (openid,))
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return dict(row)
        
        cursor.execute("""
            INSERT INTO passengers (openid, nickname) VALUES (?, ?)
        """, (openid, nickname or "乘客"))
        
        passenger_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"id": passenger_id, "openid": openid, "nickname": nickname}
    
    @staticmethod
    def get_by_id(passenger_id: int) -> Optional[dict]:
        """根据ID获取乘客"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM passengers WHERE id = ?", (passenger_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


class Order:
    """订单模型"""
    
    @staticmethod
    def create(passenger_id: int, pickup_address: str, pickup_lat: float, pickup_lng: float,
               destination_address: str, destination_lat: float, destination_lng: float,
               distance_km: float = None, estimated_fare: float = None) -> dict:
        """创建订单"""
        conn = get_db()
        cursor = conn.cursor()
        
        order_no = generate_order_no()
        
        cursor.execute("""
            INSERT INTO orders (order_no, passenger_id, pickup_address, pickup_lat, pickup_lng,
                              destination_address, destination_lat, destination_lng,
                              distance_km, estimated_fare, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (order_no, passenger_id, pickup_address, pickup_lat, pickup_lng,
              destination_address, destination_lat, destination_lng,
              distance_km, estimated_fare))
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"id": order_id, "order_no": order_no}
    
    @staticmethod
    def get_by_no(order_no: str) -> Optional[dict]:
        """根据订单号获取订单"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, d.name as driver_name, d.phone as driver_phone,
                   d.car_model, d.car_number, d.car_color
            FROM orders o
            LEFT JOIN drivers d ON o.driver_id = d.id
            WHERE o.order_no = ?
        """, (order_no,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_passenger(passenger_id: int, limit: int = 10) -> List[dict]:
        """获取乘客的订单列表"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, d.name as driver_name, d.car_model, d.car_number
            FROM orders o
            LEFT JOIN drivers d ON o.driver_id = d.id
            WHERE o.passenger_id = ?
            ORDER BY o.created_at DESC
            LIMIT ?
        """, (passenger_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def assign_driver(order_no: str, driver_id: int):
        """分配司机"""
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE orders 
            SET driver_id = ?, status = 'matched', matched_at = ?
            WHERE order_no = ?
        """, (driver_id, now, order_no))
        conn.commit()
        conn.close()
    
    @staticmethod
    def complete(order_no: str, actual_fare: float):
        """完成订单"""
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE orders 
            SET status = 'completed', actual_fare = ?,
                completed_at = ?, payment_status = 'paid'
            WHERE order_no = ?
        """, (actual_fare, now, order_no))
        
        # 更新司机完成订单数
        cursor.execute("SELECT driver_id FROM orders WHERE order_no = ?", (order_no,))
        row = cursor.fetchone()
        if row and row['driver_id']:
            cursor.execute("""
                UPDATE drivers SET total_orders = total_orders + 1 WHERE id = ?
            """, (row['driver_id'],))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def cancel(order_no: str):
        """取消订单"""
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE orders SET status = 'cancelled', completed_at = ?
            WHERE order_no = ?
        """, (now, order_no))
        conn.commit()
        conn.close()


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间距离（km）- 简化版 Haversine"""
    import math
    
    R = 6371  # 地球半径（km）
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def calculate_fare(distance_km: float) -> float:
    """计算费用"""
    base_price = 10  # 起步价（3km）
    per_km_price = 2  # 超出部分（元/km）
    
    if distance_km <= 3:
        return base_price
    
    fare = base_price + (distance_km - 3) * per_km_price
    return round(fare, 2)
