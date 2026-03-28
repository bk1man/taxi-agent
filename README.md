# 🚕 Taxi Agent MVP

智能打车 Agent，基于微信公众号的对话式打车平台。

## 功能特性

### 乘客端（公众号）
- ✅ 发送"我要打车"开始叫车
- ✅ 语音/文字输入目的地
- ✅ 查询附近可用车辆
- ✅ 选择车辆并创建订单
- ✅ 订单状态查询
- ✅ 自动支付（简化版）

### 司机端（开发中）
- [ ] 司机登录
- [ ] 接收订单推送
- [ ] 手动/自动接单
- [ ] 位置上报
- [ ] 完成行程

## 技术架构

```
乘客 → 微信公众号 → Flask Backend → SQLite
                         ↓
                   OpenClaw Agent
                         ↓
                   调度逻辑
```

## 快速开始

### 1. 启动后端服务

```bash
cd /root/projects/taxi-agent/backend
pip install flask requests
python app.py
```

### 2. 配置公众号

在微信公众号后台配置：
- URL: `http://你的服务器IP:5000/wechat/callback`
- Token: 与 `WECHAT_TOKEN` 配置一致

### 3. 测试

发送"打车"到公众号即可体验

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/driver/nearby` | GET | 查询附近司机 |
| `/api/order/create` | POST | 创建订单 |
| `/api/order/<order_no>` | GET | 查询订单状态 |
| `/api/driver/order/accept` | POST | 司机接单 |
| `/wechat/callback` | POST | 公众号回调 |

## 项目结构

```
/root/projects/taxi-agent/
├── ARCHITECTURE.md          # 完整架构设计
├── README.md                # 本文档
├── backend/
│   ├── app.py              # Flask 主应用
│   ├── models.py           # 数据模型
│   ├── agent_main.py       # Agent 主逻辑
│   ├── agent_tools.py      # Agent 工具
│   └── wechat_callback.py  # 微信回调
└── database/
    └── taxi.db             # SQLite 数据库
```

## 开发计划

- [x] MVP 基础框架
- [x] 数据库模型
- [x] 后端 API
- [x] Agent 对话逻辑
- [x] 公众号回调
- [ ] 地图 API 集成
- [ ] 微信支付集成
- [ ] 司机端 APP

## License

MIT
