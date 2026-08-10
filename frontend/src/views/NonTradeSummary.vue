<template>
  <div class="non-trade-summary-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>非交易收入/支出统计报表</span>
          <el-button type="success" plain :disabled="!hasData" @click="exportExcel">导出 Excel</el-button>
        </div>
      </template>

      <!-- 筛选区 -->
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">录入时间：</span>
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
          <div class="stat-num income">¥{{ fmt(summary.income_total) }}</div>
          <div class="stat-label">非交易收入合计</div>
        </div>
        <div class="stat-card">
          <div class="stat-num expense">¥{{ fmt(summary.expense_total) }}</div>
          <div class="stat-label">非交易支出合计</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" :class="summary.net >= 0 ? 'income' : 'expense'">¥{{ fmt(summary.net) }}</div>
          <div class="stat-label">结余（收入-支出）</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ summary.count }}</div>
          <div class="stat-label">总笔数</div>
        </div>
      </div>

      <!-- 图表：按账务代码收支对比 -->
      <div ref="chartRef" class="summary-chart" v-show="byCode.length"></div>

      <el-row :gutter="16">
        <!-- 按账务代码 -->
        <el-col :span="14">
          <div class="sub-card">
            <div class="sub-title">按账务代码汇总</div>
            <el-table :data="byCode" v-loading="loading" border size="small" max-height="400">
              <el-table-column label="账务代码" width="100" align="center">
                <template #default="{ row }"><span class="code-text">{{ row.code }}</span></template>
              </el-table-column>
              <el-table-column prop="name" label="名称" min-width="130" show-overflow-tooltip />
              <el-table-column label="类型" width="100" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.code_type === 'income' ? 'success' : 'danger'" size="small">{{ row.code_type === 'income' ? '非交易收入' : '非交易支出' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="收入合计" width="110" align="right">
                <template #default="{ row }"><span class="income-text">¥{{ fmt(row.income_total) }}</span></template>
              </el-table-column>
              <el-table-column label="支出合计" width="110" align="right">
                <template #default="{ row }"><span class="expense-text">¥{{ fmt(row.expense_total) }}</span></template>
              </el-table-column>
              <el-table-column prop="count" label="笔数" width="70" align="center" />
            </el-table>
          </div>
        </el-col>
        <!-- 按人员 -->
        <el-col :span="10">
          <div class="sub-card">
            <div class="sub-title">按人员汇总</div>
            <el-table :data="byUser" v-loading="loading" border size="small" max-height="400">
              <el-table-column prop="real_name" label="人员" min-width="90" />
              <el-table-column label="收入合计" width="110" align="right">
                <template #default="{ row }"><span class="income-text">¥{{ fmt(row.income_total) }}</span></template>
              </el-table-column>
              <el-table-column label="支出合计" width="110" align="right">
                <template #default="{ row }"><span class="expense-text">¥{{ fmt(row.expense_total) }}</span></template>
              </el-table-column>
              <el-table-column prop="count" label="笔数" width="70" align="center" />
            </el-table>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
defineOptions({ name: 'NonTradeSummary' })
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import * as XLSX from 'xlsx'
import { ElMessage } from 'element-plus'
import { getNonTradeSummary } from '@/api/nonTrade'

/**
 * 非交易收入/支出统计报表（财务模块 → 非交易收支统计，仅老板端）
 * 按录入时间筛选：汇总卡 + 按账务代码表 + 按人员表 + 收支对比柱状图 + 导出 Excel。
 */

const loading = ref(false)
const dateRange = ref(null)
const summary = ref({ income_total: 0, expense_total: 0, net: 0, count: 0 })
const byCode = ref([])
const byUser = ref([])
const hasData = computed(() => byCode.value.length > 0 || byUser.value.length > 0)

function fmt(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function doQuery() {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await getNonTradeSummary(params)
    summary.value = res.summary || { income_total: 0, expense_total: 0, net: 0, count: 0 }
    byCode.value = res.by_code || []
    byUser.value = res.by_user || []
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
  const top = byCode.value.slice(0, 10)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['收入', '支出'], top: 4 },
    grid: { left: 100, right: 30, top: 40, bottom: 30 },
    xAxis: {
      type: 'value',
      axisLabel: { formatter: (v) => (Math.abs(v) >= 10000 ? v / 10000 + '万' : v) }
    },
    yAxis: {
      type: 'category',
      data: top.map((i) => `${i.code} ${i.name}`),
      axisLabel: { width: 90, overflow: 'truncate' }
    },
    series: [
      {
        name: '收入',
        type: 'bar',
        barWidth: 10,
        data: top.map((i) => i.income_total),
        itemStyle: { color: '#67C23A', borderRadius: [0, 3, 3, 0] },
        label: { show: true, position: 'right', formatter: (p) => (p.value ? '¥' + p.value : ''), fontSize: 10 }
      },
      {
        name: '支出',
        type: 'bar',
        barWidth: 10,
        data: top.map((i) => i.expense_total),
        itemStyle: { color: '#F56C6C', borderRadius: [0, 3, 3, 0] },
        label: { show: true, position: 'right', formatter: (p) => (p.value ? '¥' + p.value : ''), fontSize: 10 }
      }
    ]
  })
}

function handleResize() {
  if (chart) chart.resize()
}

// ==================== 导出 ====================
function exportExcel() {
  const wb = XLSX.utils.book_new()
  const codeRows = byCode.value.map((i) => ({
    账务代码: i.code,
    名称: i.name,
    类型: i.code_type === 'income' ? '非交易收入' : '非交易支出',
    收入合计: i.income_total,
    支出合计: i.expense_total,
    笔数: i.count
  }))
  const ws1 = XLSX.utils.json_to_sheet(codeRows)
  XLSX.utils.book_append_sheet(wb, ws1, '按账务代码')
  const userRows = byUser.value.map((i) => ({
    人员: i.real_name,
    收入合计: i.income_total,
    支出合计: i.expense_total,
    笔数: i.count
  }))
  const ws2 = XLSX.utils.json_to_sheet(userRows)
  XLSX.utils.book_append_sheet(wb, ws2, '按人员')
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `非交易收支统计-${today}.xlsx`)
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
.non-trade-summary-container {
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
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.stat-card {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px 20px;
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.stat-num.income {
  color: #67c23a;
}

.stat-num.expense {
  color: #f56c6c;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.summary-chart {
  height: 320px;
  margin-bottom: 16px;
  border: 1px solid #f0f2f5;
  border-radius: 6px;
  background: #fff;
}

.sub-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 14px;
}

.sub-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  font-size: 14px;
}

.code-text {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #409eff;
}

.income-text {
  color: #67c23a;
  font-weight: 600;
}

.expense-text {
  color: #f56c6c;
  font-weight: 600;
}
</style>
