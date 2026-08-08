<template>
  <div class="refund-orders-container">
    <div class="body-wrap">
      <div class="table-wrap" :class="{ 'with-detail': detailVisible }">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>退款订单</span>
              <el-button type="success" plain :disabled="!items.length" @click="exportExcel">导出 Excel</el-button>
            </div>
          </template>

          <!-- 查询条件区（与毛利分析一致：下拉选择 + 自由输入模糊） -->
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
              <span class="filter-label">销售人员：</span>
              <el-select
                v-model="filters.sales_person"
                filterable clearable allow-create default-first-option
                placeholder="选择或输入" style="width: 140px"
              >
                <el-option v-for="p in options.sales_persons" :key="p" :label="p" :value="p" />
              </el-select>
            </div>
            <div class="filter-item">
              <span class="filter-label">品牌：</span>
              <el-select
                v-model="filters.brand"
                filterable clearable allow-create default-first-option
                placeholder="选择或输入" style="width: 130px"
              >
                <el-option v-for="b in options.brands" :key="b.id" :label="b.name" :value="b.name" />
              </el-select>
            </div>
            <div class="filter-item">
              <span class="filter-label">类别：</span>
              <el-select
                v-model="filters.category"
                filterable clearable allow-create default-first-option
                placeholder="选择或输入" style="width: 130px"
              >
                <el-option v-for="c in options.categories" :key="c.id" :label="c.name" :value="c.name" />
              </el-select>
            </div>
            <div class="filter-item">
              <span class="filter-label">平台订单号：</span>
              <el-input v-model="filters.platform_order_no" placeholder="模糊查询" clearable style="width: 150px" @keyup.enter="doQuery" />
            </div>
            <div class="filter-item">
              <span class="filter-label">商品名称：</span>
              <el-input v-model="filters.product_name" placeholder="模糊查询" clearable style="width: 130px" @keyup.enter="doQuery" />
            </div>
            <el-button type="primary" @click="doQuery">查询</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </div>

          <!-- 合计 -->
          <div class="totals-bar">
            <span>共 <b>{{ totalCount }}</b> 笔退款订单</span>
            <span>退款金额合计 <b>¥{{ fmt(totalAmount) }}</b></span>
          </div>

          <!-- 明细表格 -->
          <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="560" @row-click="showDetail">
            <el-table-column type="index" label="序号" width="65" align="center" />
            <el-table-column prop="platform_order_no" label="平台订单号" min-width="150" show-overflow-tooltip />
            <el-table-column prop="product_name" label="商品名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="sales_amount" label="销售金额" width="110" align="right">
              <template #default="{ row }">¥{{ fmt(row.sales_amount) }}</template>
            </el-table-column>
            <el-table-column prop="sales_person" label="销售人员" width="110" />
            <el-table-column prop="order_time" label="下单时间" min-width="160">
              <template #default="{ row }">{{ row.order_time || '—' }}</template>
            </el-table-column>
            <!-- 退款备注：截断显示，鼠标悬浮显示全文 -->
            <el-table-column prop="refund_note" label="退款备注" min-width="180" show-overflow-tooltip />
          </el-table>
        </el-card>
      </div>

      <!-- 右侧抽屉：点击行展示订单详情 -->
      <transition name="slide-left">
        <div v-if="detailVisible" class="detail-panel">
          <div class="detail-header">
            <span class="detail-title">退款订单详情</span>
            <el-button text size="small" @click="closeDetail">✕</el-button>
          </div>
          <div class="detail-body" v-if="currentRow">
            <div class="detail-row"><span class="k">平台订单号</span><span class="v">{{ currentRow.platform_order_no || '—' }}</span></div>
            <div class="detail-row"><span class="k">商品名称</span><span class="v">{{ currentRow.product_name || '—' }}</span></div>
            <div class="detail-row"><span class="k">销售金额</span><span class="v">¥{{ fmt(currentRow.sales_amount) }}</span></div>
            <div class="detail-row"><span class="k">销售人员</span><span class="v">{{ currentRow.sales_person || '—' }}</span></div>
            <div class="detail-row"><span class="k">下单时间</span><span class="v">{{ currentRow.order_time || '—' }}</span></div>
            <div class="detail-row"><span class="k">品牌</span><span class="v">{{ currentRow.brand || '—' }}</span></div>
            <div class="detail-row"><span class="k">类别</span><span class="v">{{ currentRow.category || '—' }}</span></div>
            <div class="detail-row"><span class="k">物流公司</span><span class="v">{{ currentRow.logistics_company || '—' }}</span></div>
            <div class="detail-row"><span class="k">运单号</span><span class="v">{{ currentRow.logistics_no || '—' }}<template v-if="currentRow.logistics_no_2"> / {{ currentRow.logistics_no_2 }}</template></span></div>
            <div class="detail-row"><span class="k">收货地址</span><span class="v">{{ currentRow.receiver_address || '—' }}</span></div>
            <div class="detail-row"><span class="k">备注</span><span class="v">{{ currentRow.remark || '—' }}</span></div>
            <div class="detail-row refund"><span class="k">退款备注</span><span class="v">{{ currentRow.refund_note || '—' }}</span></div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { getRefundOrders, getGrossProfitOptions } from '@/api/statistics'
import { ElMessage } from 'element-plus'

/**
 * 退款订单明细（数据统计 → 销售分析 → 退款订单）
 * 查询模式与毛利分析一致：下单时间范围 + 销售人员/品牌/类别（下拉+自由输入）+ 平台订单号/商品名称模糊。
 * 列：平台订单号/商品名称/销售金额/销售人员/下单时间/退款备注（截断，悬浮显示全文）。
 * 点击行 → 右侧抽屉展示订单详情；支持导出 Excel。
 */

const loading = ref(false)
const items = ref([])
const totalCount = ref(0)
const totalAmount = ref(0)
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
    const res = await getRefundOrders(params)
    const data = res || {}
    items.value = data.items || []
    totalCount.value = data.total_count || 0
    totalAmount.value = data.total_amount || 0
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

// ==================== 右侧抽屉：订单详情 ====================
const detailVisible = ref(false)
const currentRow = ref(null)

function showDetail(row) {
  currentRow.value = row
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  currentRow.value = null
}

function exportExcel() {
  const rows = items.value.map(i => ({
    平台订单号: i.platform_order_no || '',
    商品名称: i.product_name || '',
    销售金额: Number(i.sales_amount || 0),
    销售人员: i.sales_person || '',
    下单时间: i.order_time || '',
    退款备注: i.refund_note || '',
    普通备注: i.remark || ''
  }))
  rows.push({ 平台订单号: '合计', 销售金额: Number(totalAmount.value || 0), 退款备注: `共 ${totalCount.value} 笔` })
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '退款订单')
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `退款订单-${today}.xlsx`)
  ElMessage.success('Excel 已导出')
}

onMounted(() => {
  loadOptions()
  doQuery()
})
</script>

<style scoped>
.refund-orders-container {
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

.detail-body {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  padding: 6px 0;
  border-bottom: 1px dashed #f0f2f5;
  font-size: 13px;
}

.detail-row .k {
  width: 80px;
  color: #909399;
  flex-shrink: 0;
}

.detail-row .v {
  color: #303133;
  word-break: break-all;
}

.detail-row.refund .k {
  color: #f56c6c;
  font-weight: 600;
}

.detail-row.refund .v {
  color: #f56c6c;
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
