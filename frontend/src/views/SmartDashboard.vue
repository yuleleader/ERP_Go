<template>
  <div class="smart-dashboard">
    <!-- 顶部标题栏 -->
    <header class="dashboard-header">
      <div class="header-left">
        <span class="data-scope-tag">此面板仅统计最近24个月内数据</span>
      </div>
      <h1 class="dashboard-title">全球业务数据智慧大屏</h1>
      <div class="header-right">
        <span class="refresh-hint">自动刷新 {{ formatCountdown(refreshCountdown) }}</span>
        <span class="current-time">{{ currentTime }}</span>
        <el-button type="primary" size="small" @click="refreshData" :loading="refreshing">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="info" size="small" @click="goBack" plain>
          <el-icon><ArrowLeft /></el-icon>
          退出
        </el-button>
      </div>
    </header>

    <!-- 主体内容区 -->
    <main class="dashboard-body">
      <!-- 左侧面板 -->
      <aside class="panel panel-left">
        <!-- 核心指标卡片 -->
        <div class="stats-cards">
          <div class="stat-card">
            <div class="stat-label">总订单数</div>
            <div class="stat-value">{{ formatNumber(overview.total_orders) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">销售总金额</div>
            <div class="stat-value">¥{{ formatNumber(overview.total_sales) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">待发货订单</div>
            <div class="stat-value">{{ formatNumber(overview.pending_orders) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">生产中订单</div>
            <div class="stat-value">{{ formatNumber(overview.producing_orders) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">已发货订单</div>
            <div class="stat-value">{{ formatNumber(overview.shipped_orders) }}</div>
          </div>
          <div class="stat-card refund">
            <div class="stat-label">退款订单</div>
            <div class="stat-value">{{ formatNumber(overview.refunded_orders) }}单 · ¥{{ formatNumber(overview.refunded_amount) }}</div>
          </div>
        </div>

        <!-- 月度销售趋势 -->
        <div class="chart-block">
          <div class="block-title">月度销售趋势</div>
          <div ref="salesChartRef" class="chart-container"></div>
        </div>

        <!-- 畅销品排行 -->
        <div class="rank-block">
          <div class="block-title">畅销品排行（TOP10）</div>
          <div class="rank-list">
            <div
              v-for="(item, index) in productRanking"
              :key="index"
              class="rank-item"
            >
              <span class="rank-index" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <span class="rank-name" :title="item.product_name">{{ item.product_name }}</span>
              <span class="rank-value">{{ formatNumber(item.sales_count) }}单</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中间地图 -->
      <section class="panel panel-center">
        <div ref="mapChartRef" class="map-container"></div>
      </section>

      <!-- 右侧面板 -->
      <aside class="panel panel-right">
        <!-- 网店销售排行 -->
        <div class="table-block shop-block">
          <div class="block-title">网店销售排行TOP10</div>
          <div class="shop-list">
            <div
              v-for="(item, index) in shopRanking"
              :key="index"
              class="shop-card"
            >
              <div class="shop-card-main">
                <span class="rank-bar" :class="{ top: index < 3 }"></span>
                <span class="owner-name">{{ item.real_name }}</span>
                <span class="sales-amount">¥{{ formatNumber(item.total_sales) }}</span>
              </div>
              <div class="shop-card-sub">网店ID：{{ item.shop_id }}</div>
            </div>
            <div v-if="shopRanking.length === 0" class="empty-row">暂无数据</div>
          </div>
        </div>

        <!-- 超期订单 -->
        <div class="table-block overdue-block">
          <div class="block-title">超期订单</div>
          <div class="overdue-desc">统计未发货和虚拟发货订单，从下单时间到当前的时间差</div>
          <div class="data-table">
            <div class="table-header">
              <span class="col-order">订单ID</span>
              <span class="col-status">状态</span>
              <span class="col-time">下单时长</span>
            </div>
            <div class="table-body">
              <div
                v-for="(item, index) in overdueOrders"
                :key="index"
                class="table-row"
              >
                <span class="col-order clickable-order" :title="点击查看订单详情" @click="openDetail(item.order_id)">{{ item.order_id }}</span>
                <span class="col-status">
                  <span class="status-tag" :class="item.shipping_status">{{ item.shipping_status_text }}</span>
                </span>
                <span class="col-time">{{ item.overdue_text }}</span>
              </div>
              <div v-if="overdueOrders.length === 0" class="empty-row">暂无超期订单</div>
            </div>
          </div>
        </div>
      </aside>
    </main>

    <!-- 订单详情弹窗：点击超期订单ID后弹出，与订单列表"查看"界面一致 -->
    <OrderDetailDialog v-model="detailVisible" :order-id="detailOrderId" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts';
import { Refresh, ArrowLeft } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import {
  getOrderOverview,
  getProductRanking,
  getMonthlySales,
  getShopRanking,
  getOverdueOrders,
  getCountryDistribution
} from '@/api/dashboard';
import OrderDetailDialog from '@/components/OrderDetailDialog.vue';

// ==================== 响应式数据 ====================
const overview = ref({
  total_orders: 0,
  total_sales: 0,
  shipped_orders: 0,
  pending_orders: 0,
  producing_orders: 0,
  virtual_orders: 0,
  refunded_orders: 0,
  refunded_amount: 0
});

const productRanking = ref([]);
const shopRanking = ref([]);
const overdueOrders = ref([]);
// 订单详情弹窗状态
const detailVisible = ref(false);
const detailOrderId = ref('');

function openDetail(orderId) {
  detailOrderId.value = orderId;
  detailVisible.value = true;
}
const monthlySales = ref([]);
const countryDistribution = ref([]);
const refreshing = ref(false);
const currentTime = ref('');
// 自动刷新倒计时（秒），每隔 3 分钟统计刷新一次
const REFRESH_INTERVAL = 3 * 60;
const refreshCountdown = ref(REFRESH_INTERVAL);

// ==================== ECharts 实例 ====================
let salesChart = null;
let mapChart = null;

const salesChartRef = ref(null);
const mapChartRef = ref(null);

let timeTimer = null;

// ==================== 工具函数 ====================
function formatNumber(num) {
  if (!num) return '0';
  return Number(num).toLocaleString('zh-CN');
}

function updateCurrentTime() {
  const now = new Date();
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

// 1 秒心跳：更新时间 + 自动刷新倒计时（归零时触发数据刷新）
function tick() {
  updateCurrentTime();
  if (refreshCountdown.value <= 1) {
    refreshCountdown.value = REFRESH_INTERVAL;
    fetchData();
  } else {
    refreshCountdown.value -= 1;
  }
}

function formatCountdown(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ==================== 数据加载 ====================
async function fetchData() {
  refreshing.value = true;
  try {
    const [overviewRes, productRes, monthlyRes, shopRes, overdueRes, countryRes] = await Promise.all([
      getOrderOverview(),
      getProductRanking({ limit: 10 }),
      getMonthlySales({ months: 24 }),
      getShopRanking({ limit: 10 }),
      getOverdueOrders({ limit: 20 }),
      getCountryDistribution()
    ]);

    overview.value = overviewRes || {};
    productRanking.value = (productRes?.data || []).map((item, index) => ({
      rank: index + 1,
      product_name: item.product_name || '未知商品',
      sales_count: item.sales_count || 0,
      total_revenue: item.total_revenue || 0
    }));
    monthlySales.value = monthlyRes?.data || [];
    shopRanking.value = (shopRes?.data || []).map((item, index) => ({
      rank: index + 1,
      real_name: item.real_name || '—',
      shop_id: item.shop_id,
      shop_name: item.shop_name || item.shop_id,
      shop_account: item.shop_account || '—',
      order_count: item.order_count || 0,
      total_sales: item.total_sales || 0
    }));
    overdueOrders.value = overdueRes?.data || [];
    countryDistribution.value = countryRes?.data || [];

    updateCharts();
  } catch (error) {
    console.error('获取大屏数据失败:', error);
    ElMessage.error('获取大屏数据失败');
  } finally {
    refreshing.value = false;
  }
}

function refreshData() {
  refreshCountdown.value = REFRESH_INTERVAL;
  fetchData();
}

// 退出大屏：返回订单管理页面
const router = useRouter();
function goBack() {
  router.push('/orders');
}

// ==================== 图表初始化与更新 ====================

// 热力色：按归一化值 t∈[0,1] 在 蓝→青→黄→红 之间线性插值
function heatColor(t) {
  t = Math.max(0, Math.min(1, t))
  const stops = [
    [0.0, [37, 99, 235]],   // 蓝
    [0.34, [0, 212, 255]],  // 青
    [0.67, [251, 191, 36]], // 黄
    [1.0, [239, 68, 68]]    // 红
  ]
  let a = stops[0]
  let b = stops[stops.length - 1]
  for (let i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i][0] && t <= stops[i + 1][0]) {
      a = stops[i]
      b = stops[i + 1]
      break
    }
  }
  const span = (b[0] - a[0]) || 1
  const f = (t - a[0]) / span
  const r = Math.round(a[1][0] + (b[1][0] - a[1][0]) * f)
  const g = Math.round(a[1][1] + (b[1][1] - a[1][1]) * f)
  const bl = Math.round(a[1][2] + (b[1][2] - a[1][2]) * f)
  return `rgb(${r}, ${g}, ${bl})`
}

function initCharts() {
  if (salesChartRef.value) {
    salesChart = echarts.init(salesChartRef.value);
  }
  if (mapChartRef.value) {
    mapChart = echarts.init(mapChartRef.value);
  }
}

function updateCharts() {
  updateSalesChart();
  updateMapChart();
}

function updateSalesChart() {
  if (!salesChart) return;

  const data = monthlySales.value.slice(-12); // 最近12个月
  const xData = data.map(item => item.label);
  const yData = data.map(item => item.sales);

  salesChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#3b82f6',
      textStyle: { color: '#fff' },
      formatter: params => `${params[0].name}<br/>销售额: ¥${formatNumber(params[0].value)}`
    },
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 11,
        formatter: value => value >= 10000 ? (value / 10000) + '万' : value
      }
    },
    series: [{
      data: yData,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        color: '#00d4ff',
        width: 3
      },
      itemStyle: {
        color: '#00d4ff',
        borderColor: '#fff',
        borderWidth: 1
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
          { offset: 1, color: 'rgba(0, 212, 255, 0.02)' }
        ])
      }
    }]
  }, true);
}

// 地图：按收货地址识别国家，国家级呼吸点（点大小按订单金额缩放）

async function updateMapChart() {
  if (!mapChart) return;

  // 加载世界地图 GeoJSON（仅到国家层级）
  let worldJson;
  try {
    const response = await fetch('/map/world.json');
    worldJson = await response.json();
    echarts.registerMap('world', worldJson);
  } catch (error) {
    console.error('加载世界地图数据失败:', error);
    return;
  }

  const list = countryDistribution.value || [];
  const maxAmount = list.reduce((m, d) => Math.max(m, d.total_amount || 0), 0) || 1;

  // 呼吸点数据：name=国家中文名，value=[经度, 纬度, 订单金额]
  const scatterData = list.map(item => {
    const amount = item.total_amount || 0;
    // 金额归一化 → 热力色（蓝→青→黄→红）
    const t = maxAmount > 0 ? Math.min(1, amount / maxAmount) : 0;
    const c = heatColor(t);
    return {
      name: item.country_cn,
      value: [item.coord[0], item.coord[1], amount],
      // 每个点单独上色（呼吸涟漪/光晕同步取该色）
      itemStyle: {
        color: c,
        shadowBlur: 12,
        shadowColor: c.replace('rgb', 'rgba').replace(')', ', 0.8)')
      },
      // 额外信息用于悬浮提示
      info: {
        totalAmount: amount,
        heatT: t,
        totalCount: item.total_count || 0,
        shippedCount: item.shipped_count || 0,
        unshippedCount: item.unshipped_count || 0
      }
    };
  });

  mapChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: '#3b82f6',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: params => {
        if (params.seriesType === 'effectScatter' && params.data && params.data.info) {
          const i = params.data.info;
          const amountColor = heatColor(i.heatT || 0);
          return `
            <div style="font-weight:bold;margin-bottom:4px;">${params.name}</div>
            <div>总订单金额：<span style="color:${amountColor};">¥${formatNumber(i.totalAmount)}</span></div>
            <div>总订单数：${i.totalCount}</div>
            <div>已发货数：<span style="color:#52c41a;">${i.shippedCount}</span></div>
            <div>未发货数：<span style="color:#ff7875;">${i.unshippedCount}</span></div>
          `;
        }
        return params.name;
      }
    },
    geo: {
      map: 'world',
      roam: true,
      zoom: 1.2,
      center: [60, 30],
      label: {
        show: false
      },
      itemStyle: {
        areaColor: 'rgba(20, 60, 120, 0.4)',
        borderColor: 'rgba(0, 212, 255, 0.3)',
        borderWidth: 1
      },
      emphasis: {
        itemStyle: {
          areaColor: 'rgba(30, 90, 170, 0.6)'
        },
        label: { show: false }
      }
    },
    series: [
      {
        name: '国家订单分布',
        type: 'effectScatter',
        coordinateSystem: 'geo',
        data: scatterData,
        // 呼吸点大小按订单金额缩放（14~42px）
        symbolSize: val => {
          const amount = val[2] || 0;
          return Math.max(14, 14 + (amount / maxAmount) * 28);
        },
        showEffectOn: 'render',
        rippleEffect: {
          brushType: 'stroke',
          scale: 3.5,
          period: 4
        },
        // 颜色由每个数据点的 itemStyle.color 决定（按金额热力渐变）
        zlevel: 2
      }
    ]
  }, true);
}

// ==================== 生命周期 ====================
function handleResize() {
  salesChart?.resize();
  mapChart?.resize();
}

onMounted(() => {
  initCharts();
  fetchData();
  updateCurrentTime();
  timeTimer = setInterval(tick, 1000);
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer);
  window.removeEventListener('resize', handleResize);
  salesChart?.dispose();
  mapChart?.dispose();
});
</script>

<style scoped>
.smart-dashboard {
  width: 100%;
  min-height: 100vh;
  padding: 16px;
  background: linear-gradient(135deg, #020617 0%, #0f172a 50%, #1e293b 100%);
  color: #e2e8f0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 顶部标题栏 */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  position: relative;
}

.data-scope-tag {
  padding: 4px 12px;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 4px;
  font-size: 13px;
  color: #93c5fd;
}

.dashboard-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  margin: 0;
  font-size: 28px;
  font-weight: bold;
  letter-spacing: 8px;
  color: #fff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.current-time {
  font-size: 14px;
  color: #94a3b8;
  font-family: 'Courier New', monospace;
}

.refresh-hint {
  font-size: 13px;
  color: #38bdf8;
  font-family: 'Courier New', monospace;
  white-space: nowrap;
}

/* 主体布局 */
.dashboard-body {
  flex: 1;
  display: grid;
  grid-template-columns: 320px 1fr 360px;
  gap: 16px;
  min-height: 0;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

/* 左侧面板：垂直三等分（卡片 / 图表 / 排行），防止下块被遮挡 */
.panel-left {
  overflow: hidden;
}

/* 通用块样式 */
.block-title {
  font-size: 16px;
  font-weight: bold;
  color: #fff;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  display: flex;
  align-items: center;
}

.block-title::before {
  content: '';
  width: 4px;
  height: 16px;
  background: linear-gradient(180deg, #00d4ff, #3b82f6);
  margin-right: 8px;
  border-radius: 2px;
}

/* 统计卡片（三等分中的第一段：等高） */
.stats-cards {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-auto-rows: 1fr;
  gap: 10px;
}

.stat-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 0;
  overflow: hidden;
  transition: all 0.3s ease;
}

.stat-card:hover {
  border-color: rgba(0, 212, 255, 0.4);
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.15);
  transform: translateY(-2px);
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 4px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-value {
  font-size: 17px;
  font-weight: bold;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

/* 退款订单卡片（暖色调区分） */
.stat-card.refund {
  border-color: rgba(255, 107, 107, 0.35);
}

.stat-card.refund:hover {
  border-color: rgba(255, 107, 107, 0.6);
  box-shadow: 0 0 15px rgba(255, 107, 107, 0.18);
}

.stat-card.refund .stat-label {
  color: #fda4af;
}

.stat-card.refund .stat-value {
  color: #fecaca;
}

/* 图表块（三等分中的第二段：等高） */
.chart-block {
  flex: 1;
  min-height: 0;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-container {
  flex: 1;
  min-height: 0;
}

/* 排行块（三等分中的第三段：等高） */
.rank-block {
  flex: 1;
  min-height: 0;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rank-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(15, 23, 42, 0.4);
  border-radius: 6px;
  font-size: 13px;
}

.rank-index {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.2);
  color: #94a3b8;
  font-weight: bold;
  font-size: 12px;
  flex-shrink: 0;
}

.rank-index.top {
  background: linear-gradient(135deg, #f59e0b, #ef4444);
  color: #fff;
}

.rank-name {
  flex: 1;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-value {
  color: #00d4ff;
  font-family: 'Courier New', monospace;
  flex-shrink: 0;
}

/* 中间地图 */
.panel-center {
  background: rgba(30, 41, 59, 0.3);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 600px;
}

/* 表格块 */
.table-block {
  flex: 1;
  min-height: 260px;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
}

.overdue-block {
  flex: 1.2;
}

.overdue-desc {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
  line-height: 1.5;
}

.data-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 1fr 70px 80px;
  gap: 8px;
  padding: 10px 8px;
  font-size: 13px;
  align-items: center;
}

.overdue-block .table-header,
.overdue-block .table-row {
  grid-template-columns: 1fr 70px 80px;
}

.table-header {
  background: rgba(59, 130, 246, 0.15);
  border-radius: 6px;
  color: #93c5fd;
  font-weight: bold;
}

.table-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
}

.table-row {
  background: rgba(15, 23, 42, 0.4);
  border-radius: 6px;
  color: #e2e8f0;
}

.col-name,
.col-order {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clickable-order {
  color: #38bdf8;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-style: dashed;
  text-underline-offset: 3px;
}

.clickable-order:hover {
  color: #7dd3fc;
}

.col-amount,
.col-time {
  text-align: right;
  color: #00d4ff;
  font-family: 'Courier New', monospace;
}

/* 网店销售排行：卡片式排行条目（无表头） */
.shop-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shop-card {
  background: rgba(22, 27, 34, 0.8);
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 12px 14px 10px;
}

.shop-card-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rank-bar {
  flex-shrink: 0;
  width: 3px;
  height: 22px;
  border-radius: 2px;
  background: rgba(148, 163, 184, 0.4);
}

.rank-bar.top {
  background: linear-gradient(180deg, #f59e0b, #d97706);
}

.owner-name {
  font-size: 13px;
  color: #e6edf3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.sales-amount {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 15px;
  font-weight: bold;
  color: #67e8f9;
  font-family: 'Courier New', monospace;
}

.shop-card-sub {
  margin-top: 4px;
  padding-left: 11px; /* 与 rank-bar 对齐 */
  font-size: 12px;
  color: #8b949e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.2);
  color: #94a3b8;
  font-size: 12px;
  font-weight: bold;
}

.rank-badge.top {
  background: linear-gradient(135deg, #f59e0b, #ef4444);
  color: #fff;
}

.status-tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.status-tag.pending {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.status-tag.virtual_shipped {
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
}

.empty-row {
  text-align: center;
  padding: 30px;
  color: #64748b;
  font-size: 13px;
}

/* 响应式 */
@media (max-width: 1400px) {
  .dashboard-body {
    grid-template-columns: 280px 1fr 320px;
  }
}

@media (max-width: 1200px) {
  .dashboard-body {
    grid-template-columns: 1fr;
  }

  .panel-center {
    min-height: 500px;
  }
}
</style>
