<template>
  <div class="gross-profit-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>毛利分析</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="border-card" @tab-change="handleTabChange">
        <el-tab-pane
          v-for="tab in tabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
        >
          <!-- 查询条件区（每个页签独立状态；下拉选择 + 自由输入模糊） -->
          <div class="filter-bar">
            <div class="filter-item">
              <span class="filter-label">{{ tab.timeLabel }}：</span>
              <el-date-picker
                v-model="tabState[tab.key].dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                style="width: 250px"
              />
            </div>
            <div class="filter-item">
              <span class="filter-label">销售人员：</span>
              <el-select
                v-model="tabState[tab.key].filters.sales_person"
                filterable clearable allow-create default-first-option
                placeholder="选择或输入" style="width: 140px"
              >
                <el-option v-for="p in options.sales_persons" :key="p" :label="p" :value="p" />
              </el-select>
            </div>
            <div class="filter-item">
              <span class="filter-label">品牌：</span>
              <el-select
                v-model="tabState[tab.key].filters.brand"
                filterable clearable allow-create default-first-option
                placeholder="选择或输入" style="width: 130px"
              >
                <el-option v-for="b in options.brands" :key="b.id" :label="b.name" :value="b.name" />
              </el-select>
            </div>
            <div class="filter-item">
              <span class="filter-label">类别：</span>
              <el-select
                v-model="tabState[tab.key].filters.category"
                filterable clearable allow-create default-first-option
                placeholder="选择或输入" style="width: 130px"
              >
                <el-option v-for="c in options.categories" :key="c.id" :label="c.name" :value="c.name" />
              </el-select>
            </div>
            <div class="filter-item">
              <span class="filter-label">平台订单号：</span>
              <el-input v-model="tabState[tab.key].filters.platform_order_no" placeholder="模糊查询" clearable style="width: 150px" @keyup.enter="doQuery(tab.key)" />
            </div>
            <div class="filter-item">
              <span class="filter-label">商品名称：</span>
              <el-input v-model="tabState[tab.key].filters.product_name" placeholder="模糊查询" clearable style="width: 130px" @keyup.enter="doQuery(tab.key)" />
            </div>
            <el-button type="primary" @click="doQuery(tab.key)">查询</el-button>
            <el-button @click="resetQuery(tab.key)">重置</el-button>
            <div class="filter-spacer"></div>
            <el-button type="success" plain :disabled="!tabState[tab.key].items.length" @click="exportExcel(tab.key)">导出 Excel</el-button>
          </div>

          <!-- 合计 -->
          <div class="totals-bar">
            <span>共 <b>{{ tabState[tab.key].totalCount }}</b> 笔订单</span>
            <span>毛利合计 <b>¥{{ fmt(tabState[tab.key].totalGrossProfit) }}</b></span>
          </div>

          <!-- 明细表格 -->
          <el-table :data="tabState[tab.key].items" v-loading="tabState[tab.key].loading" border style="width: 100%" max-height="560">
            <el-table-column type="index" label="序号" width="65" align="center" />
            <el-table-column prop="platform_order_no" label="平台订单号" min-width="150" show-overflow-tooltip />
            <el-table-column prop="product_name" label="商品名称" min-width="150" />
            <el-table-column prop="gross_profit" label="毛利" width="110" align="right">
              <template #default="{ row }">¥{{ fmt(row.gross_profit) }}</template>
            </el-table-column>
            <el-table-column prop="sales_person" label="销售人员" width="100" />
            <el-table-column prop="brand" label="品牌" width="100" />
            <el-table-column prop="category" label="类别" width="110" />
            <el-table-column v-if="tab.key === 'order'" prop="order_time" label="下单时间" min-width="160">
              <template #default="{ row }">{{ row.order_time || '—' }}</template>
            </el-table-column>
            <template v-else>
              <el-table-column prop="shipping_time" label="发货时间" min-width="160">
                <template #default="{ row }">{{ row.shipping_time || '—' }}</template>
              </el-table-column>
              <el-table-column prop="order_id" label="订单号" min-width="180" show-overflow-tooltip />
            </template>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { getGrossProfitList, getGrossProfitOptions } from '@/api/statistics'
import { ElMessage } from 'element-plus'

/**
 * 毛利分析报表（数据统计 → 毛利分析）
 * 两个页签：按下单时间统计 / 按发货时间统计，各自独立的查询条件与数据。
 * 毛利 = orders.gross_profit（销售金额 - 商品成本价，系统自动计算存储）。
 * 筛选：销售人员/品牌/类别（下拉+自由输入）、平台订单号/商品名称（模糊），可组合。
 */

const tabs = [
  { key: 'order', label: '按下单时间统计', timeLabel: '下单时间' },
  { key: 'shipping', label: '按发货时间统计', timeLabel: '发货时间' }
]
const activeTab = ref('order')

function makeTabState() {
  return {
    dateRange: null,
    filters: { sales_person: '', brand: '', category: '', platform_order_no: '', product_name: '' },
    items: [],
    totalGrossProfit: 0,
    totalCount: 0,
    loading: false,
    loaded: false
  }
}
const tabState = reactive({})
tabs.forEach(t => { tabState[t.key] = makeTabState() })

const options = reactive({ sales_persons: [], brands: [], categories: [] })

function fmt(v) {
  const n = Number(v || 0)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadOptions() {
  try {
    const o = await getGrossProfitOptions()
    options.sales_persons = o.sales_persons || []
    options.brands = o.brands || []
    options.categories = o.categories || []
  } catch (e) {
    /* 下拉选项加载失败不影响查询 */
  }
}

async function doQuery(key) {
  const st = tabState[key]
  st.loading = true
  try {
    const params = { time_type: key }
    if (st.dateRange && st.dateRange.length === 2) {
      params.start_date = st.dateRange[0]
      params.end_date = st.dateRange[1]
    }
    Object.keys(st.filters).forEach(k => {
      const v = st.filters[k]
      if (v && String(v).trim()) params[k] = String(v).trim()
    })
    const res = await getGrossProfitList(params)
    const data = res || {}
    st.items = data.items || []
    st.totalGrossProfit = data.total_gross_profit || 0
    st.totalCount = data.total_count || 0
    st.loaded = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '查询失败')
  } finally {
    st.loading = false
  }
}

function resetQuery(key) {
  const st = tabState[key]
  st.dateRange = null
  Object.keys(st.filters).forEach(k => { st.filters[k] = '' })
  doQuery(key)
}

// 切换页签：首次进入自动查询
function handleTabChange(key) {
  const st = tabState[key]
  if (!st.loaded && !st.loading) {
    doQuery(key)
  }
}

function exportExcel(key) {
  const tab = tabs.find(t => t.key === key)
  const st = tabState[key]
  const cols = key === 'shipping'
    ? ['平台订单号', '商品名称', '毛利', '销售人员', '品牌', '类别', '订单号', '发货时间']
    : ['平台订单号', '商品名称', '毛利', '销售人员', '品牌', '类别', '下单时间']
  const rows = st.items.map(i => {
    const o = {
      平台订单号: i.platform_order_no,
      商品名称: i.product_name,
      毛利: Number(i.gross_profit || 0),
      销售人员: i.sales_person,
      品牌: i.brand,
      类别: i.category
    }
    if (key === 'shipping') {
      o.订单号 = i.order_id || ''
      o.发货时间 = i.shipping_time || ''
    } else {
      o.下单时间 = i.order_time || ''
    }
    return o
  })
  rows.push({ 平台订单号: '合计', 毛利: Number(st.totalGrossProfit || 0) })
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, tab.label)
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `毛利分析-${tab.label}-${today}.xlsx`)
  ElMessage.success('Excel 已导出')
}

onMounted(() => {
  loadOptions()
  doQuery('order')
})
</script>

<style scoped>
.gross-profit-container {
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
