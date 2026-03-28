/**
 * 司机端前端逻辑
 * 对接后端 API: /api/driver/login, /api/driver/status, /api/driver/location,
 *              /api/driver/order/accept, /api/driver/order/complete
 */

const API_BASE = 'http://localhost:5000/api';

// 状态
let currentDriver = null;
let currentOrder = null;
let locationInterval = null;
let currentStatus = 'offline';

// ========== 工具函数 ==========

function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast ' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 2500);
}

function $(id) { return document.getElementById(id); }

// ========== 登录 ==========

async function driverLogin() {
    const phone = $('loginPhone').value.trim();
    if (!phone || phone.length < 11) {
        showToast('请输入正确的手机号', 'error');
        return;
    }

    const btn = document.getElementById('loginBtn');
    btn.disabled = true;
    btn.textContent = '登录中...';

    try {
        const resp = await fetch(`${API_BASE}/driver/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone })
        });
        const data = await resp.json();

        if (data.code === 0) {
            currentDriver = data.data;
            localStorage.setItem('driver', JSON.stringify(currentDriver));
            enterMainScreen();
        } else {
            showToast(data.message || '登录失败', 'error');
        }
    } catch (e) {
        // 离线模式：模拟登录
        if (e.name === 'TypeError' && e.message.includes('fetch')) {
            currentDriver = {
                driver_id: 1,
                name: '测试司机',
                phone: '13800138000',
                car_model: '比亚迪汉 EV',
                car_number: '京A·12345',
                status: 'offline'
            };
            localStorage.setItem('driver', JSON.stringify(currentDriver));
            enterMainScreen();
            showToast('离线模式（后端未启动）', 'info');
        } else {
            showToast('网络错误: ' + e.message, 'error');
        }
    } finally {
        btn.disabled = false;
        btn.textContent = '登录';
    }
}

// 回车登录
$('loginPhone').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') driverLogin();
});

// ========== 主界面 ==========

function enterMainScreen() {
    $('loginScreen').classList.add('hidden');
    $('mainScreen').classList.add('active');

    // 填充司机信息
    if (currentDriver) {
        $('driverName').textContent = currentDriver.name;
        $('driverCar').textContent = `${currentDriver.car_model} · ${currentDriver.car_number}`;
        currentStatus = currentDriver.status || 'offline';
        updateStatusUI();
    }

    // 加载历史订单
    loadHistory();
}

function driverLogout() {
    if (!confirm('确定退出登录？')) return;
    localStorage.removeItem('driver');
    currentDriver = null;
    currentOrder = null;
    stopLocationUpdates();
    $('mainScreen').classList.remove('active');
    $('loginScreen').classList.remove('hidden');
    $('loginPhone').value = '';
    showToast('已退出登录');
}

// ========== 状态切换 ==========

async function setStatus(status) {
    currentStatus = status;
    updateStatusUI();

    if (!currentDriver) return;

    try {
        await fetch(`${API_BASE}/driver/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ driver_id: currentDriver.driver_id, status })
        });
        showToast('状态已更新为：' + statusText(status), 'success');

        if (status === 'online') {
            startLocationUpdates();
        } else {
            stopLocationUpdates();
        }
    } catch (e) {
        console.warn('状态更新失败（离线模式）:', e.message);
        if (status === 'online') startLocationUpdates();
        showToast('状态已切换为：' + statusText(status) + '（离线模式）', 'info');
    }
}

function toggleStatus() {
    const next = currentStatus === 'offline' ? 'online' : 'offline';
    setStatus(next);
}

function updateStatusUI() {
    const badge = $('statusBadge');
    badge.className = 'status-badge ' + currentStatus;
    badge.textContent = statusText(currentStatus);

    document.querySelectorAll('.status-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === currentStatus);
    });
}

function statusText(status) {
    return { offline: '离线', online: '接单中', busy: '勿扰' }[status] || '离线';
}

// ========== 位置上报 ==========

function startLocationUpdates() {
    if (locationInterval) return;
    $('mapStatus').textContent = '🟢 接单模式 - 位置上报中';

    // 模拟位置（实际项目中应使用 navigator.geolocation）
    let step = 0;
    const baseLat = 39.908;
    const baseLng = 116.397;

    locationInterval = setInterval(async () => {
        step++;
        // 模拟轻微移动
        const lat = (baseLat + (Math.random() - 0.5) * 0.002).toFixed(6);
        const lng = (baseLng + (Math.random() - 0.5) * 0.002).toFixed(6);
        const now = new Date().toLocaleTimeString('zh-CN');

        // 打印到地图日志
        const log = $('locationLog');
        const entry = document.createElement('div');
        entry.textContent = `[${now}] 上报位置: ${lat}, ${lng}`;
        log.insertBefore(entry, log.firstChild);
        if (log.children.length > 20) log.removeChild(log.lastChild);

        // 发给后端
        if (currentDriver && currentStatus === 'online') {
            try {
                await fetch(`${API_BASE}/driver/location`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ driver_id: currentDriver.driver_id, latitude: lat, longitude: lng })
                });
            } catch (e) {
                console.warn('位置上报失败（离线模式）');
            }
        }
    }, 10000); // 每10秒

    // 立即上报一次
    const now = new Date().toLocaleTimeString('zh-CN');
    const log = $('locationLog');
    log.innerHTML = `<div>[${now}] 位置服务已启动</div>`;
}

function stopLocationUpdates() {
    if (locationInterval) {
        clearInterval(locationInterval);
        locationInterval = null;
    }
    $('mapStatus').textContent = '位置服务已停止';
}

// ========== 订单处理 ==========

async function acceptOrder(orderNo) {
    if (!currentDriver) return;

    try {
        const resp = await fetch(`${API_BASE}/driver/order/accept`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ driver_id: currentDriver.driver_id, order_no: orderNo })
        });
        const data = await resp.json();

        if (data.code === 0) {
            currentOrder = data.data;
            currentOrder.order_no = orderNo;
            showToast('接单成功！', 'success');
            renderCurrentOrder();
        } else {
            showToast(data.message || '接单失败', 'error');
            // 刷新订单
            renderCurrentOrder();
        }
    } catch (e) {
        // 离线模式模拟接单
        currentOrder = {
            order_no: orderNo,
            status: 'matched',
            pickup_address: '北京市朝阳区东直门外大街',
            destination_address: '北京市海淀区中关村大街'
        };
        showToast('接单成功（离线模式）', 'success');
        renderCurrentOrder();
    }
}

async function rejectOrder(orderNo) {
    showToast('已拒绝订单', 'info');
    renderCurrentOrder();
}

async function completeTrip() {
    if (!currentOrder) return;

    const actualFare = (Math.random() * 20 + 15).toFixed(1); // 模拟费用 15~35
    try {
        const resp = await fetch(`${API_BASE}/driver/order/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_no: currentOrder.order_no, actual_fare: parseFloat(actualFare) })
        });
        const data = await resp.json();

        if (data.code === 0) {
            showToast(`行程完成！收入 ¥${actualFare}`, 'success');
            currentOrder = null;
            renderCurrentOrder();
            loadHistory();
        } else {
            showToast(data.message || '完成失败', 'error');
        }
    } catch (e) {
        showToast(`行程完成（离线模式）收入 ¥${actualFare}`, 'success');
        currentOrder = null;
        renderCurrentOrder();
        loadHistory();
    }
}

function renderCurrentOrder() {
    const area = $('orderArea');

    if (!currentOrder) {
        area.innerHTML = `
            <div class="order-card no-order">
                <div class="icon">📭</div>
                <p>暂无待处理订单</p>
                <p style="font-size:12px;margin-top:6px;">${currentStatus === 'online' ? '正在为您寻找附近乘客...' : '开启接单后将自动匹配'}</p>
            </div>`;
        return;
    }

    area.innerHTML = `
        <div class="order-card">
            <div class="order-number">订单号：${currentOrder.order_no}</div>
            <div class="order-route">
                <div class="route-point">
                    <div class="route-dot start"></div>
                    <div>
                        <div class="route-label">上车点</div>
                        <div class="route-address">${currentOrder.pickup_address}</div>
                    </div>
                </div>
                <div class="route-line"></div>
                <div class="route-point">
                    <div class="route-dot end"></div>
                    <div>
                        <div class="route-label">目的地</div>
                        <div class="route-address">${currentOrder.destination_address}</div>
                    </div>
                </div>
            </div>
            ${currentOrder.status === 'pending' ? `
                <div class="order-actions">
                    <button class="btn btn-accept" onclick="acceptOrder('${currentOrder.order_no}')">✅ 接单</button>
                    <button class="btn btn-reject" onclick="rejectOrder('${currentOrder.order_no}')">❌ 拒单</button>
                </div>` : `
                <button class="btn btn-complete" onclick="completeTrip()">🏁 完成行程</button>`}
        </div>`;
}

// ========== 历史订单 ==========

async function loadHistory() {
    // 模拟历史数据（实际项目中可新增 API）
    const area = $('historyArea');
    const mockHistory = [
        { order_no: 'ORD-20260328-001', time: '今天 14:30', from: '朝阳区望京SOHO', to: '海淀区五道口', fare: '28.5' },
        { order_no: 'ORD-20260328-002', time: '今天 10:15', from: '东城区王府井', to: '朝阳区三里屯', fare: '19.8' }
    ];

    area.innerHTML = mockHistory.map(o => `
        <div class="history-card">
            <div class="order-info">
                <span class="order-time">${o.time}</span>
                <span class="order-fare">¥${o.fare}</span>
            </div>
            <div class="order-from">📍 ${o.from}</div>
            <div class="order-to">🎯 ${o.to}</div>
        </div>`).join('');
}

// ========== 模拟订单（测试）============

async function createMockOrder() {
    // 模拟推送一个订单到前端
    const orderNo = 'ORD-' + Date.now();
    currentOrder = {
        order_no: orderNo,
        status: 'pending',
        pickup_address: '北京市朝阳区东直门外大街 18号',
        destination_address: '北京市朝阳区望京SOHO T3'
    };
    renderCurrentOrder();
    showToast('模拟订单已创建，请点击接单', 'success');
}

// ========== 底部 Tab 切换 ==========

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
}

// ========== 初始化 ==========

(function init() {
    // 检查本地登录状态
    const saved = localStorage.getItem('driver');
    if (saved) {
        try {
            currentDriver = JSON.parse(saved);
            enterMainScreen();
        } catch (e) {
            localStorage.removeItem('driver');
        }
    }

    // 显示/隐藏模拟测试面板（开发环境）
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
        $('mockPanel').style.display = 'block';
    }
})();
