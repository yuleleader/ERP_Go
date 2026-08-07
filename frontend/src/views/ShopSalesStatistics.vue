<template>
  <div class="shop-sales-container">
    <div class="body-wrap">
      <div class="table-wrap" :class="{ 'with-detail': detailVisible }">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>网店销售统计</span>
              <el-button type="success" plain :disabled="!items.length" @click="exportExcel">导出 Excel</el-button>
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
                style="width: 250px"
              />
            </div>
            <div class="filter-item">
              <span class="filter-label">网店ID：</span>
              <el-input v-model="filters.shop_id" placeholder="模糊查询" clearable style="width: 180px" @keyup.enter="doQuery" />
            </div>
            <div class="filter-item">
              <span class="filter-label">创建者：</span>
              <el-select
                v-model="filters.creator"
                filterable clearable allow-create default-first-option
                placeholder="选择或输入" style="width: 140px"
              >
                <el-option v-for="c in creatorOptions" :key="c" :label="c" :value="c" />
              </el-select>
            </div>
            <el-button type="primary" @click="doQuery">查询</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </div>

          <!-- 合计 -->
          <div class="totals-bar">
            <span>销售金额合计 <b>¥{{ fmt(totals.sales_amount) }}</b></span>
            <span>总订单数 <b>{{ totals.total_orders }}</b></span>
            <span>退货金额 <b>¥{{ fmt(totals.refund_amount) }}</b></span>
            <span>退订单数 <b>{{ totals.refund_count }}</b></span>
          </div>

          <!-- 明细表格 -->
          <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="560">
            <el-table-column type="index" label="序号" width="65" align="center" />
            <el-table-column prop="shop_id" label="网店ID" min-width="220" show-overflow-tooltip />
            <el-table-column prop="creator" label="创建者" min-width="120" />
            <el-table-column prop="sales_amount" label="销售金额" width="130" align="right">
              <template #default="{ row }">¥{{ fmt(row.sales_amount) }}</template>
            </el-table-column>
            <el-table-column prop="total_orders" label="总订单数" width="110" align="right">
              <template #default="{ row }">
                <a class="link-cell" @click="showShopDetail(row, false)">{{ row.total_orders }}</a>
              </template>
            </el-table-column>
            <el-table-column prop="refund_amount" label="退货金额" width="130" align="right">
              <template #default="{ row }">¥{{ fmt(row.refund_amount) }}</template>
            </el-table-column>
            <el-table-column prop="refund_count" label="退订单数" width="110" align="right">
              <template #default="{ row }">
                <a class="link-cell" @click="showShopDetail(row, true)">{{ row.refund_count }}</a>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- 右侧抽屉：订单明细 -->
      <transition name="slide-left">
        <div v-if="detailVisible" class="detail-panel">
          <div class="detail-header">
            <span class="detail-title">{{ detailTitle }}</span>
            <el-button text size="small" @click="closeDetail">✕</el-button>
          </div>
          <el-table
            :data="detailItems"
            v-loading="detailLoading"
            border
            size="small"
            max-height="calc(100vh - 220px)"
          >
            <el-table-column prop="platform_order_no" label="平台订单号" min-width="180" show-overflow-tooltip />
            <el-table-column prop="product_name" label="商品名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="shipping_status_text" label="订单状态" width="110" align="center" />
            <el-table-column label="订单金额" width="110" align="right">
              <template #default="{ row }">¥{{ fmt(row.sales_amount) }}</template>
            </el-table-column>
          </el-table>
          <div class="detail-footer">共 {{ detailTotal }} 单</div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { getShopSalesSummary, getSummaryOrderDetails } from '@/api/statistics'
import { getShops } from '@/api/shop'
import { ElMessage } from 'element-plus'

/**
 * 网店销售统计（数据统计 → 网店销售统计）
 * 按网店分组：网店ID / 创建者 / 销售金额 / 总订单数 / 退货金额 / 退订单数。
 * 支持按下单时间段筛选、网店ID模糊、创建者（下拉+自由输入）。
 * 口径：销售金额=非退款单合计；总订单数=全部订单（含退款）；退货金额/退订单数=refunded。
 */

const loading = ref(false)
const items = ref([])
const totals = reactive({ sales_amount: 0, total_orders: 0, refund_amount: 0, refund_count: 0 })
const dateRange = ref(null)
const creatorOptions = ref([])

const filters = reactive({
  shop_id: '',
  creator: ''
})

function fmt(v) {
  const n = Number(v || 0)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadCreators() {
  try {
    const shops = await getShops()
    const list = Array.isArray(shops) ? shops : (shops.data || [])
    creatorOptions.value = [...new Set(list.map(s => s.creator).filter(Boolean))]
  } catch (e) {
    /* 下拉选项加载失败不影响查询 */
  }
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
    const res = await getShopSalesSummary(params)
    const data = res || {}
    items.value = data.items || []
    const t = data.totals || {}
    totals.sales_amount = t.sales_amount || 0
    totals.total_orders = t.total_orders || 0
    totals.refund_amount = t.refund_amount || 0
    totals.refund_count = t.refund_count || 0
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

// ==================== 订单明细钻取（右侧抽屉） ====================
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailItems = ref([])
const detailTitle = ref('')
const detailTotal = ref(0)

async function showShopDetail(row, onlyRefunded) {
  const params = { mode: 'shop', shop_id: row.shop_id || '', only_refunded: onlyRefunded }
  if (dateRange.value && dateRange.value.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  detailVisible.value = true
  detailLoading.value = true
  detailItems.value = []
  detailTitle.value = `网店 ${row.shop_id || '未知'} · ${onlyRefunded ? '退货订单' : '全部订单'}`
  try {
    const res = await getSummaryOrderDetails(params)
    detailItems.value = (res && res.items) || []
    detailTotal.value = (res && res.total) || 0
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '明细加载失败')
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detailVisible.value = false
  detailItems.value = []
  detailTotal.value = 0
}

function exportExcel() {
  const rows = items.value.map(i => ({
    网店ID: i.shop_id,
    创建者: i.creator,
    销售金额: Number(i.sales_amount || 0),
    总订单数: i.total_orders,
    退货金额: Number(i.refund_amount || 0),
    退订单数: i.refund_count
  }))
  rows.push({ 网店ID: '合计', 创建者: '', 销售金额: Number(totals.sales_amount || 0), 总订单数: totals.total_orders, 退货金额: Number(totals.refund_amount || 0), 退订单数: totals.refund_count })
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '网店销售统计')
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `网店销售统计-${today}.xlsx`)
  ElMessage.success('Excel 已导出')
}

onMounted(() => {
  loadCreators()
  doQuery()
})
</script>

<style scoped>
.shop-sales-container {
  padding: 20px;
}

.body-wrap {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.table-wrap {
  flex: 1;
  min-width: 0;
}

.table-wrap.with-detail {
  flex: none;
  width: calc(100% - 480px);
}

.detail-panel {
  flex: none;
  width: 460px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.detail-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.detail-footer {
  margin-top: 10px;
  color: #909399;
  font-size: 13px;
}

.link-cell {
  color: #409eff;
  cursor: pointer;
  text-decoration: underline;
}

.link-cell:hover {
  color: #66b1ff;
}

/* 抽屉滑入动画 */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.25s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  opacity: 0;
  transform: translateX(40px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
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
  flex-wrap: wrap;
}

.totals-bar b {
  color: #409eff;
}
</style>
