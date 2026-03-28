# 司机端 (Driver App)

出租车调度系统司机端 Web 页面，纯 HTML + JavaScript，无需后端渲染。

## 📁 文件结构

```
driver-app/
├── index.html   # 司机端页面
├── driver.js    # 前端逻辑
└── README.md    # 说明文档
```

## 🚀 快速启动

```bash
# 方式一：直接在浏览器打开
open driver-app/index.html

# 方式二：用 Python HTTP Server（支持 API 调用）
cd /root/projects/taxi-agent
python3 -m http.server 8080
# 浏览器访问 http://localhost:8080/driver-app/

# 方式三：用 Node.js serve
npx serve driver-app/
```

> ⚠️ 前后端分离开发时，后端运行在 `http://localhost:5000`，前端页面中 `driver.js` 的 `API_BASE` 已配置为该地址。

## 🔗 对接 API

| 功能 | 接口 | 方法 |
|------|------|------|
| 司机登录 | `/api/driver/login` | POST |
| 更新状态 | `/api/driver/status` | POST |
| 上报位置 | `/api/driver/location` | POST |
| 接受订单 | `/api/driver/order/accept` | POST |
| 完成行程 | `/api/driver/order/complete` | POST |

> 所有 API 遵循 RESTful 规范，详情见 `backend/app.py`。

## 🎯 功能清单

- [x] 司机登录（手机号验证）
- [x] 状态切换（离线 / 接单 / 勿扰）
- [x] 模拟位置上报（每 10 秒打印一次坐标，并 POST 到后端）
- [x] 订单展示（上车点 / 目的地路线）
- [x] 接单 / 拒单
- [x] 行程完成（含模拟费用计算）
- [x] 历史行程展示
- [x] 离线模式（后端不可用时自动降级）
- [x] 响应式设计（适配手机 / 桌面）
- [x] 本地登录状态持久化（localStorage）
- [x] 模拟订单测试面板（仅 localhost 显示）

## 📱 页面布局

```
┌─────────────────────────┐
│  🚕 司机  比亚迪汉 · 京A  │  ← 顶部：司机信息 + 状态徽章
├─────────────────────────┤
│      🗺️ 地图占位区域      │  ← 位置日志实时显示
│  [位置: 39.908, 116.397] │
├─────────────────────────┤
│ [离线]  [接单]  [勿扰]   │  ← 状态切换
├─────────────────────────┤
│      📋 当前订单         │
│  上车点：朝阳区东直门...  │
│  目的地：望京SOHO T3     │
│  [接单]  [拒单]          │
├─────────────────────────┤
│      📜 历史行程         │
│  14:30 望京SOHO→五道口 ¥28.5 │
└─────────────────────────┘
```

## 🧪 测试

**测试手机号**：`13800138000`

本地启动后端：
```bash
cd /root/projects/taxi-agent/backend
python3 app.py
```

## 🔧 配置

如需修改后端地址，编辑 `driver.js` 顶部：

```javascript
const API_BASE = 'http://localhost:5000/api';  // 改这里
```

## 📝 开发说明

- 前端不依赖任何框架（零依赖），便于嵌入任何 WebView
- 位置模拟使用随机坐标，真实场景应替换为 `navigator.geolocation`
- 离线模式下所有 API 调用会打印警告但不会崩溃
- 登录状态通过 `localStorage` 持久化，刷新不丢失
