<template>
  <div class="sales-statistics-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>销售统计</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="border-card" @tab-change="handleTabChange">
        <el-tab-pane
          v-for="tab in tabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
        >
          <!-- 查询条件区（每个页签独立状态） -->
          <div class="filter-bar">
            <div class="filter-item">
              <span class="filter-label">{{ tab.nameLabel }}：</span>
              <el-input
                v-model="tabState[tab.key].keyword"
                :placeholder="'输入' + tab.nameLabel + '模糊查询'"
                clearable
                style="width: 220px"
                @keyup.enter="doQuery(tab.key)"
              />
            </div>
            <div class="filter-item">
              <span class="filter-label">下单时间：</span>
              <el-date-picker
                v-model="tabState[tab.key].dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                style="width: 260px"
              />
            </div>
            <el-button type="primary" @click="doQuery(tab.key)">查询</el-button>
            <el-button @click="resetQuery(tab.key)">重置</el-button>
            <div class="filter-spacer"></div>
            <el-button type="success" plain :disabled="!tabState[tab.key].items.length" @click="exportExcel(tab.key)">
              导出 Excel
            </el-button>
          </div>

          <!-- 汇总合计 -->
          <div class="totals-bar">
            <span>合计：销售金额 <b>¥{{ fmt(tabState[tab.key].totals.sales_amount) }}</b></span>
            <span>销售数量 <b>{{ tabState[tab.key].totals.sales_count }}</b></span>
            <span>毛利 <b>¥{{ fmt(tabState[tab.key].totals.gross_profit) }}</b></span>
          </div>

          <!-- 数据表格 -->
          <el-table
            :data="tabState[tab.key].items"
            v-loading="tabState[tab.key].loading"
            border
            style="width: 100%"
            max-height="560"
          >
            <el-table-column type="index" label="序号" width="70" align="center" />
            <el-table-column :prop="tab.nameField" :label="tab.nameLabel" min-width="200" />
            <el-table-column prop="sales_amount" label="销售金额" width="140" align="right">
              <template #default="{ row }">¥{{ fmt(row.sales_amount) }}</template>
            </el-table-column>
            <el-table-column prop="sales_count" label="销售数量" width="110" align="right" />
            <el-table-column prop="gross_profit" label="毛利" width="140" align="right">
              <template #default="{ row }">¥{{ fmt(row.gross_profit) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { getSalesSummary } from '@/api/statistics'
import { ElMessage } from 'element-plus'

/**
 * 销售统计报表（数据统计 → 销售统计）
 * 四个页签：人员/类别（二级）/品牌/商品 销售汇总
 * 每个页签独立的查询条件、时间范围、表格与导出（互不影响）。
 * 指标口径：销售金额=sum(sales_amount)；销售数量=订单数（系统无数量字段，每单按 1 件计）；
 * 毛利=销售金额-商品成本价（products 表按商品名匹配，未匹配或未填成本按 0）。
 */

const tabs = [
  { key: 'person', label: '人员销售汇总', nameLabel: '真实姓名', nameField: 'name', queryType: 'person' },
  { key: 'category', label: '类别销售汇总', nameLabel: '二级分类名称', nameField: 'name', queryType: 'category' },
  { key: 'brand', label: '品牌销售汇总', nameLabel: '品牌名称', nameField: 'name', queryType: 'brand' },
  { key: 'product', label: '商品销售汇总', nameLabel: '商品名称', nameField: 'name', queryType: 'product' }
]

const activeTab = ref('person')

// 每个页签独立状态
function makeTabState() {
  return {
    keyword: '',
    dateRange: null,
    items: [],
    totals: { sales_amount: 0, sales_count: 0, gross_profit: 0 },
    loading: false,
    loaded: false
  }
}
const tabState = reactive({})
tabs.forEach(t => { tabState[t.key] = makeTabState() })

function fmt(v) {
  const n = Number(v || 0)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function doQuery(key) {
  const st = tabState[key]
  st.loading = true
  try {
    const tab = tabs.find(t => t.key === key)
    const params = { summary_type: tab.queryType }
    if (st.keyword && st.keyword.trim()) params.keyword = st.keyword.trim()
    if (st.dateRange && st.dateRange.length === 2) {
      params.start_date = st.dateRange[0]
      params.end_date = st.dateRange[1]
    }
    const res = await getSalesSummary(params)
    const data = res || {}
    st.items = data.items || []
    st.totals = data.totals || { sales_amount: 0, sales_count: 0, gross_profit: 0 }
    st.loaded = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '查询失败')
  } finally {
    st.loading = false
  }
}

function resetQuery(key) {
  const st = tabState[key]
  st.keyword = ''
  st.dateRange = null
  doQuery(key)
}

// 切换页签：若该页签从未查询过，自动加载一次
function handleTabChange(key) {
  const st = tabState[key]
  if (!st.loaded && !st.loading) {
    doQuery(key)
  }
}

// 导出当前页签筛选后的数据为 Excel（xlsx 前端生成）
function exportExcel(key) {
  const tab = tabs.find(t => t.key === key)
  const st = tabState[key]
  const rows = st.items.map(i => ({
    [tab.nameLabel]: i.name,
    销售金额: Number(i.sales_amount || 0),
    销售数量: i.sales_count,
    毛利: Number(i.gross_profit || 0)
  }))
  rows.push({
    [tab.nameLabel]: '合计',
    销售金额: Number(st.totals.sales_amount || 0),
    销售数量: st.totals.sales_count,
    毛利: Number(st.totals.gross_profit || 0)
  })
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, tab.label)
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `销售统计-${tab.label}-${today}.xlsx`)
  ElMessage.success('Excel 已导出')
}

onMounted(() => {
  doQuery('person')
})
</script>

<style scoped>
.sales-statistics-container {
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
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
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
