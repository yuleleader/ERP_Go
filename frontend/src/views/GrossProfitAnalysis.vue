<template>
  <div class="gross-profit-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ pageTitle }}</span>
        </div>
      </template>

      <!-- 查询条件区 -->
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">{{ timeLabel }}：</span>
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
          <span class="filter-label">销售人员：</span>
          <el-select
            v-model="filters.sales_person"
            filterable
            clearable
            allow-create
            default-first-option
            placeholder="选择或输入"
            style="width: 150px"
          >
            <el-option v-for="p in options.sales_persons" :key="p" :label="p" :value="p" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">品牌：</span>
          <el-select
            v-model="filters.brand"
            filterable
            clearable
            allow-create
            default-first-option
            placeholder="选择或输入"
            style="width: 150px"
          >
            <el-option v-for="b in options.brands" :key="b.id" :label="b.name" :value="b.name" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">类别：</span>
          <el-select
            v-model="filters.category"
            filterable
            clearable
            allow-create
            default-first-option
            placeholder="选择或输入"
            style="width: 150px"
          >
            <el-option v-for="c in options.categories" :key="c.id" :label="c.name" :value="c.name" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">平台订单号：</span>
          <el-input v-model="filters.platform_order_no" placeholder="模糊查询" clearable style="width: 170px" @keyup.enter="doQuery" />
        </div>
        <div class="filter-item">
          <span class="filter-label">商品名称：</span>
          <el-input v-model="filters.product_name" placeholder="模糊查询" clearable style="width: 150px" @keyup.enter="doQuery" />
        </div>
        <el-button type="primary" @click="doQuery">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
        <div class="filter-spacer"></div>
        <el-button type="success" plain :disabled="!items.length" @click="exportExcel">导出 Excel</el-button>
      </div>

      <!-- 合计 -->
      <div class="totals-bar">
        <span>共 <b>{{ totalCount }}</b> 笔订单</span>
        <span>毛利合计 <b>¥{{ fmt(totalGrossProfit) }}</b></span>
      </div>

      <!-- 明细表格 -->
      <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="560">
        <el-table-column type="index" label="序号" width="65" align="center" />
        <el-table-column prop="platform_order_no" label="平台订单号" min-width="150" />
        <el-table-column prop="product_name" label="商品名称" min-width="160" />
        <el-table-column prop="gross_profit" label="毛利" width="120" align="right">
          <template #default="{ row }">¥{{ fmt(row.gross_profit) }}</template>
        </el-table-column>
        <el-table-column prop="sales_person" label="销售人员" width="110" />
        <el-table-column prop="brand" label="品牌" width="120" />
        <el-table-column prop="category" label="类别" width="140" />
        <el-table-column :prop="timeField" :label="timeLabel2" min-width="165">
          <template #default="{ row }">{{ row[timeField] || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="timeType === 'shipping'" prop="order_id" label="订单号" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import * as XLSX from 'xlsx'
import { getGrossProfitList, getGrossProfitOptions } from '@/api/statistics'
import { ElMessage } from 'element-plus'

/**
 * 毛利分析报表（数据统计 → 毛利分析）
 * 同一组件按路由 mode 渲染两种口径：
 * - order    ：按下单时间统计（时间=下单时间）
 * - shipping ：按发货时间统计（时间=发货时间，含订单号列）
 * 筛选：销售人员/品牌/类别/平台订单号/商品名称（下拉选择 + 自由输入模糊，可组合）。
 * 毛利 = orders.gross_profit（销售金额 - 商品成本价，系统自动计算存储）。
 */

const route = useRoute()
const timeType = computed(() => (route.query.mode === 'shipping' ? 'shipping' : 'order'))

const pageTitle = computed(() =>
  timeType.value === 'shipping' ? '毛利分析（按发货时间统计）' : '毛利分析（按下单时间统计）'
)
const timeLabel = computed(() => (timeType.value === 'shipping' ? '发货时间' : '下单时间'))
const timeLabel2 = computed(() => (timeType.value === 'shipping' ? '发货时间' : '下单时间'))
const timeField = computed(() => (timeType.value === 'shipping' ? 'shipping_time' : 'order_time'))

const loading = ref(false)
const items = ref([])
const totalGrossProfit = ref(0)
const totalCount = ref(0)
const dateRange = ref(null)

const filters = reactive({
  sales_person: '',
  brand: '',
  category: '',
  platform_order_no: '',
  product_name: ''
})

const options = reactive({ sales_persons: [], brands: [], categories: [] })

function fmt(v) {
  const n = Number(v || 0)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function doQuery() {
  loading.value = true
  try {
    const params = { time_type: timeType.value }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    Object.keys(filters).forEach(k => {
      const v = filters[k]
      if (v && String(v).trim()) params[k] = String(v).trim()
    })
    const res = await getGrossProfitList(params)
    const data = res || {}
    items.value = data.items || []
    totalGrossProfit.value = data.total_gross_profit || 0
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
  const cols = timeType.value === 'shipping'
    ? ['平台订单号', '商品名称', '毛利', '销售人员', '品牌', '类别', '订单号', '发货时间']
    : ['平台订单号', '商品名称', '毛利', '销售人员', '品牌', '类别', '下单时间']
  const rows = items.value.map(i => ({
    平台订单号: i.platform_order_no,
    商品名称: i.product_name,
    毛利: Number(i.gross_profit || 0),
    销售人员: i.sales_person,
    品牌: i.brand,
    类别: i.category,
    订单号: i.order_id || '',
    下单时间: i.order_time || '',
    发货时间: i.shipping_time || ''
  }))
  // 仅保留当前口径需要的列
  const filtered = rows.map(r => {
    const o = {}
    cols.forEach(c => { o[c] = r[c] !== undefined ? r[c] : '' })
    return o
  })
  filtered.push({ ...Object.fromEntries(cols.map(c => [c, ''])), 平台订单号: '合计', 毛利: Number(totalGrossProfit.value || 0) })
  const ws = XLSX.utils.json_to_sheet(filtered)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, pageTitle.value)
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `${pageTitle.value}-${today}.xlsx`)
  ElMessage.success('Excel 已导出')
}

onMounted(async () => {
  try {
    const o = await getGrossProfitOptions()
    options.sales_persons = o.sales_persons || []
    options.brands = o.brands || []
    options.categories = o.categories || []
  } catch (e) {
    /* 下拉选项加载失败不影响查询 */
  }
  doQuery()
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
