<template>
  <div class="freight-statistics-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>运费统计</span>
        </div>
      </template>

      <!-- 查询条件区 -->
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
        <div class="filter-item">
          <span class="filter-label">平台订单号：</span>
          <el-input v-model="filters.platform_order_no" placeholder="模糊查询" clearable style="width: 180px" @keyup.enter="doQuery" />
        </div>
        <div class="filter-item">
          <span class="filter-label">快递公司：</span>
          <el-input v-model="filters.logistics_company" placeholder="模糊查询" clearable style="width: 160px" @keyup.enter="doQuery" />
        </div>
        <el-button type="primary" @click="doQuery">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
        <div class="filter-spacer"></div>
        <el-button type="success" plain :disabled="!items.length" @click="exportExcel">导出 Excel</el-button>
      </div>

      <!-- 合计 -->
      <div class="totals-bar">
        <span>共 <b>{{ totalCount }}</b> 笔订单</span>
        <span>运费合计 <b>¥{{ fmt(totalFreight) }}</b></span>
      </div>

      <!-- 明细表格 -->
      <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="560">
        <el-table-column type="index" label="序号" width="65" align="center" />
        <el-table-column prop="platform_order_no" label="平台订单号" min-width="170" show-overflow-tooltip />
        <el-table-column prop="logistics_no" label="运单号1" min-width="150" />
        <el-table-column prop="logistics_no_2" label="运单号2" min-width="150">
          <template #default="{ row }">{{ row.logistics_no_2 || '—' }}</template>
        </el-table-column>
        <el-table-column prop="freight" label="运费" width="110" align="right">
          <template #default="{ row }">¥{{ fmt(row.freight) }}</template>
        </el-table-column>
        <el-table-column prop="logistics_company" label="快递公司" min-width="140">
          <template #default="{ row }">{{ row.logistics_company || '—' }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { getFreightList } from '@/api/statistics'
import { ElMessage } from 'element-plus'

/**
 * 运费统计报表（数据统计 → 运费统计）
 * 按下单时间段筛选；列：平台订单号 / 运单号1 / 运单号2 / 运费 / 快递公司；
 * 支持平台订单号、快递公司模糊查询；可导出 Excel（含合计行）。
 * 口径：按下单时间（created_at），退款单不计入。
 */

const loading = ref(false)
const items = ref([])
const totalFreight = ref(0)
const totalCount = ref(0)
const dateRange = ref(null)

const filters = reactive({
  platform_order_no: '',
  logistics_company: ''
})

function fmt(v) {
  const n = Number(v || 0)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function doQuery() {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    Object.keys(filters).forEach(k => {
      const v = filters[k]
      if (v && String(v).trim()) params[k] = String(v).trim()
    })
    const res = await getFreightList(params)
    const data = res || {}
    items.value = data.items || []
    totalFreight.value = data.total_freight || 0
    totalCount.value = data.total_count || 0
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '查询失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  dateRange.value = null
  Object.keys(filters).forEach(k => { filters[k] = '' })
  doQuery()
}

function exportExcel() {
  const rows = items.value.map(i => ({
    平台订单号: i.platform_order_no,
    运单号1: i.logistics_no,
    运单号2: i.logistics_no_2,
    运费: Number(i.freight || 0),
    快递公司: i.logistics_company
  }))
  rows.push({ 平台订单号: '合计', 运单号1: '', 运单号2: '', 运费: Number(totalFreight.value || 0), 快递公司: '' })
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '运费统计')
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `运费统计-${today}.xlsx`)
  ElMessage.success('Excel 已导出')
}

onMounted(() => {
  doQuery()
})
</script>

<style scoped>
.freight-statistics-container {
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

.filter-spacer {
  flex: 1;
}

.totals-bar {
  display: flex;
  gap: 24px;
  padding: 10px 14px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 14px;
  font-size: 14px;
  color: #606266;
}

.totals-bar b {
  color: #409eff;
}
</style>
