<template>
  <div class="refund-rate-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>退款率分析</span>
          <el-button type="success" plain :disabled="!items.length" @click="exportExcel">导出 Excel</el-button>
        </div>
      </template>

      <!-- 筛选区 -->
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">下单时间：</span>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
        </div>
        <el-button type="primary" @click="doQuery">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
      </div>

      <!-- 汇总卡片 -->
      <div class="stat-cards">
        <div class="stat-card">
          <div class="stat-num">{{ summary.total_orders }}</div>
          <div class="stat-label">总订单数（单）</div>
        </div>
        <div class="stat-card">
          <div class="stat-num refund">{{ summary.refund_orders }}</div>
          <div class="stat-label">退款订单数（单）</div>
        </div>
        <div class="stat-card">
          <div class="stat-num rate">{{ summary.refund_rate }}%</div>
          <div class="stat-label">整体退款率</div>
        </div>
      </div>

      <!-- 图表：各网店退款率柱状图 -->
      <div ref="chartRef" class="refund-chart" v-show="items.length"></div>

      <!-- 明细表格 -->
      <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="520">
        <el-table-column label="序号" width="65" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column prop="shop_name" label="网店名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="total_orders" label="总订单数" width="120" align="center">
          <template #default="{ row }">{{ row.total_orders }}</template>
        </el-table-column>
        <el-table-column prop="refund_orders" label="退款订单数" width="120" align="center">
          <template #default="{ row }">
            <span class="refund-num">{{ row.refund_orders }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="refund_rate" label="退款率" min-width="220" align="left">
          <template #default="{ row }">
            <div class="rate-cell">
              <div class="rate-bar-wrap">
                <div
                  class="rate-bar"
                  :class="rateClass(row.refund_rate)"
                  :style="{ width: Math.min(row.refund_rate, 100) + '%' }"
                />
              </div>
              <span class="rate-text" :class="rateClass(row.refund_rate)">{{ row.refund_rate }}%</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
defineOptions({ name: 'RefundRateAnalysis' })
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import * as XLSX from 'xlsx'
import { ElMessage } from 'element-plus'
import { getRefundRate } from '@/api/statistics'

/**
 * 退款率分析（数据统计 → 退款率分析，仅老板端）
 * 按下单时间筛选，按网店统计退款率（退款订单数/总订单数）；表格 + 柱状图 + 汇总卡 + 导出 Excel。
 */

const loading = ref(false)
const items = ref([])
const summary = reactive({ total_orders: 0, refund_orders: 0, refund_rate: 0 })
const dateRange = ref(null)

async function doQuery() {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await getRefundRate(params)
    items.value = res.items || []
    Object.assign(summary, res.summary || {})
    await nextTick()
    renderChart()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '查询失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  dateRange.value = null
  doQuery()
}

// ==================== 图表 ====================
const chartRef = ref(null)
let chart = null

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const top = items.value.slice(0, 15).slice().reverse() // 取前15个（自下而上）
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params[0]
        const row = top[p.dataIndex]
        return `${row.shop_name}<br/>退款率：${row.refund_rate}%（退款 ${row.refund_orders}/${row.total_orders} 单）`
      }
    },
    grid: { left: 140, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'value', name: '退款率(%)', max: 100 },
    yAxis: {
      type: 'category',
      data: top.map((i) => i.shop_name),
      axisLabel: { width: 120, overflow: 'truncate' }
    },
    series: [{
      name: '退款率',
      type: 'bar',
      barWidth: 14,
      data: top.map((i) => i.refund_rate),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#67C23A' },
          { offset: 0.5, color: '#E6A23C' },
          { offset: 1, color: '#F56C6C' }
        ]),
        borderRadius: [0, 4, 4, 0]
      },
      label: { show: true, position: 'right', formatter: '{c}%', fontSize: 11 }
    }]
  })
}

function handleResize() {
  if (chart) chart.resize()
}

function rateClass(rate) {
  if (rate >= 20) return 'high'
  if (rate >= 10) return 'mid'
  return 'low'
}

// ==================== 导出 ====================
function exportExcel() {
  const rows = items.value.map((i) => ({
    网店名称: i.shop_name,
    总订单数: i.total_orders,
    退款订单数: i.refund_orders,
    退款率: `${i.refund_rate}%`
  }))
  rows.push({ 网店名称: '合计', 总订单数: summary.total_orders, 退款订单数: summary.refund_orders, 退款率: `${summary.refund_rate}%` })
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '退款率分析')
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `退款率分析-${today}.xlsx`)
  ElMessage.success('Excel 已导出')
}

onMounted(() => {
  doQuery()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.refund-rate-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-label {
  color: #606266;
  font-size: 14px;
  white-space: nowrap;
}

.stat-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px 20px;
}

.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-num.refund {
  color: #f56c6c;
}

.stat-num.rate {
  color: #e6a23c;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.refund-chart {
  height: 360px;
  margin-bottom: 16px;
  border: 1px solid #f0f2f5;
  border-radius: 6px;
  background: #fff;
}

.refund-num {
  color: #f56c6c;
  font-weight: 600;
}

.rate-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rate-bar-wrap {
  flex: 1;
  height: 14px;
  background: #f0f2f5;
  border-radius: 7px;
  overflow: hidden;
}

.rate-bar {
  height: 100%;
  border-radius: 7px;
  transition: width 0.4s;
}

.rate-bar.low {
  background: #67c23a;
}

.rate-bar.mid {
  background: #e6a23c;
}

.rate-bar.high {
  background: #f56c6c;
}

.rate-text {
  min-width: 56px;
  font-weight: 600;
  font-size: 13px;
}

.rate-text.low {
  color: #67c23a;
}

.rate-text.mid {
  color: #e6a23c;
}

.rate-text.high {
  color: #f56c6c;
}
</style>
