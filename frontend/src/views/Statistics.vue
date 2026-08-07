<template>
  <div class="statistics-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据总览</span>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <template v-else>
        <!-- 老板端统计：5 个卡片压缩至一行 -->
        <template v-if="isBoss">
          <div class="stat-cards-row">
            <el-card class="stat-card">
              <div class="stat-icon total-sales">
                <el-icon><Money /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">¥{{ statistics.totalSales.toLocaleString() }}</div>
                <div class="stat-label">订单总金额</div>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-icon order-count">
                <el-icon><ShoppingCart /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ statistics.totalOrders }}</div>
                <div class="stat-label">总订单数</div>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-icon shipped">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ statistics.shippedOrders }}</div>
                <div class="stat-label">已发货订单</div>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-icon pending">
                <el-icon><Clock /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ statistics.pendingOrders }}</div>
                <div class="stat-label">待发货订单</div>
              </div>
            </el-card>
            <el-card class="stat-card">
              <div class="stat-icon avg-shipping">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ avgShippingTime.avg_days }}天</div>
                <div class="stat-label">平均发货时长</div>
              </div>
            </el-card>
          </div>
        </template>

        <!-- 销售端统计 -->
        <template v-if="isSales">
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon total-sales">
                  <el-icon><Money /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">¥{{ statistics.totalSales.toLocaleString() }}</div>
                  <div class="stat-label">我的销售总金额</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon order-count">
                  <el-icon><ShoppingCart /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.totalOrders }}</div>
                  <div class="stat-label">我的订单数</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </template>

        <!-- 工厂端和发货端统计 -->
        <template v-if="isFactory || isShipping">
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="8">
              <el-card class="stat-card">
                <div class="stat-icon order-count">
                  <el-icon><Box /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.totalOrders }}</div>
                  <div class="stat-label">总订单数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="stat-card">
                <div class="stat-icon pending">
                  <el-icon><Clock /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.pendingOrders }}</div>
                  <div class="stat-label">待处理订单</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="stat-card">
                <div class="stat-icon shipped">
                  <el-icon><CircleCheck /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.shippedOrders }}</div>
                  <div class="stat-label">已完成订单</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </template>

        <!-- 销售金额趋势折线图（X 轴=下单时间，Y 轴=金额汇总） -->
        <el-card class="trend-card">
          <template #header>
            <div class="trend-header">
              <span>销售金额趋势（近 {{ trendDays }} 天，按下单时间）</span>
              <div class="trend-total">累计 ¥{{ trendTotal.toLocaleString() }}</div>
            </div>
          </template>
          <div ref="trendChartRef" class="trend-chart"></div>
        </el-card>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/store/user';
import { getOverviewStatistics, getAvgShippingTime, getSalesTrend } from '@/api/statistics';
import { ElMessage } from 'element-plus';
import { Money, ShoppingCart, CircleCheck, Clock, Box, Loading, Timer } from '@element-plus/icons-vue';
import * as echarts from 'echarts';

const router = useRouter();
const userStore = useUserStore();

const isBoss = computed(() => userStore.role === 'boss');
const isSales = computed(() => userStore.role === 'sales');
const isFactory = computed(() => userStore.role === 'factory');
const isShipping = computed(() => userStore.role === 'shipping');

const loading = ref(false);

const statistics = reactive({
  totalSales: 0,
  totalOrders: 0,
  shippedOrders: 0,
  pendingOrders: 0
});

const avgShippingTime = reactive({
  avg_days: 0,
  avg_hours: 0
});

// 销售趋势折线图
const trendChartRef = ref(null);
let trendChart = null;
const trendDays = ref(30);
const trendTotal = ref(0);

async function loadTrend() {
  try {
    const res = await getSalesTrend({ days: trendDays.value })
    const data = res || {}
    const items = data.items || []
    trendTotal.value = data.total_amount || 0
    await nextTick()
    if (!trendChartRef.value) return
    if (!trendChart) {
      trendChart = echarts.init(trendChartRef.value)
    }
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 70, right: 30, top: 30, bottom: 50 },
      xAxis: {
        type: 'category',
        data: items.map(i => i.date),
        axisLabel: { rotate: 40 }
      },
      yAxis: { type: 'value', name: '金额(¥)' },
      series: [{
        name: '销售金额',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: items.map(i => i.amount),
        lineStyle: { width: 2.5, color: '#409EFF' },
        itemStyle: { color: '#409EFF' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.25)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
          ])
        }
      }]
    })
  } catch (e) {
    console.error('加载销售趋势失败', e)
  }
}

function handleResize() {
  if (trendChart) trendChart.resize()
}

const fetchStatistics = async () => {
  loading.value = true;
  try {
    const overview = await getOverviewStatistics();
    statistics.totalSales = overview.total_sales || 0;
    statistics.totalOrders = overview.total_orders || 0;
    statistics.shippedOrders = overview.shipped_orders || 0;
    statistics.pendingOrders = overview.pending_orders || 0;

    // 获取平均发货时长（所有角色都可以查看）
    const avgTime = await getAvgShippingTime();
    avgShippingTime.avg_days = avgTime.avg_days || 0;
    avgShippingTime.avg_hours = avgTime.avg_hours || 0;

    loadTrend();
  } catch (error) {
    console.error('获取统计数据失败:', error);
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录已过期，请重新登录');
      router.push('/login');
    } else {
      ElMessage.error('获取统计数据失败');
    }
  } finally {
    loading.value = false;
  }
};

const initPage = async () => {
  if (!userStore.token) {
    router.push('/login');
    return;
  }

  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo();
    } catch (e) {
      console.error('获取用户信息失败:', e);
      router.push('/login');
      return;
    }
  }

  fetchStatistics();
};

onMounted(() => {
  window.addEventListener('resize', handleResize);
  initPage();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (trendChart) {
    trendChart.dispose();
    trendChart = null;
  }
});
</script>

<style scoped>
.statistics-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.date-filter {
  display: flex;
  gap: 10px;
  align-items: center;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #999;
}

.loading-container .el-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

/* 老板端 5 个卡片压缩至一行 */
.stat-cards-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-cards-row .stat-card {
  flex: 1;
  min-width: 0;
  padding: 16px 12px;
}

.stat-cards-row .stat-icon {
  width: 48px;
  height: 48px;
  font-size: 22px;
  margin-right: 12px;
  flex-shrink: 0;
}

.stat-cards-row .stat-value {
  font-size: 20px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-cards-row .stat-label {
  font-size: 12px;
  white-space: nowrap;
}

/* 销售趋势折线图 */
.trend-card {
  margin-top: 20px;
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trend-total {
  font-size: 14px;
  color: #409eff;
  font-weight: 600;
}

.trend-chart {
  width: 100%;
  height: 360px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
  margin-right: 20px;
}

.stat-icon.total-sales { background: linear-gradient(135deg, #4facfe, #00f2fe); }
.stat-icon.order-count { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-icon.shipped { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.stat-icon.pending { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-icon.theoretical { background: linear-gradient(135deg, #fa709a, #fee140); }
.stat-icon.actual { background: linear-gradient(135deg, #a18cd1, #fbc2eb); }
.stat-icon.avg-shipping { background: linear-gradient(135deg, #4facfe, #00f2fe); }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}

.commission-detail {
  padding: 10px;
}

.commission-amount {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.amount-label {
  font-size: 14px;
  color: #666;
}

.amount-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
}

.amount-value.theoretical {
  color: #fa709a;
}

.amount-value.actual {
  color: #a18cd1;
}

.commission-info {
  font-size: 14px;
  color: #666;
  margin-bottom: 15px;
}

.commission-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #999;
  padding: 10px;
  background: #fafafa;
  border-radius: 4px;
}

.commission-note .el-icon {
  font-size: 14px;
  color: #409EFF;
  flex-shrink: 0;
  margin-top: 2px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.table-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.table-header-right .el-select {
  width: 180px;
}

.table-header-right .el-date-picker {
  width: 260px;
}

.table-header-right .el-select .el-input__wrapper,
.table-header-right .el-date-picker .el-input__wrapper {
  padding-right: 30px;
}

.table-header-right .el-select-dropdown__item {
  height: 40px;
  line-height: 40px;
  padding: 0 16px;
}

.table-summary {
  display: flex;
  gap: 20px;
}

.summary-item {
  font-size: 14px;
  color: #666;
}

.summary-item strong {
  color: #409EFF;
}

.commission-highlight {
  color: #fa709a;
  font-weight: bold;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #999;
}

.empty-state .el-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.commission-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>