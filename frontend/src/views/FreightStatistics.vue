<template>
  <div class="freight-statistics-container">
    <div class="body-wrap">
      <div class="table-wrap" :class="{ 'with-detail': detailVisible }">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>运费统计</span>
              <!-- 导出按钮位于标题所在行最右侧，响应式自适应 -->
              <el-button
                type="success"
                plain
                :disabled="!items.length"
                @click="exportExcel"
              >
                导出 Excel
              </el-button>
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
          </div>

          <!-- 合计 -->
          <div class="totals-bar">
            <span>共 <b>{{ totalCount }}</b> 笔订单</span>
            <span>运费合计 <b>¥{{ fmt(totalFreight) }}</b></span>
          </div>

          <!-- 明细表格 -->
          <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="560" @row-click="showDetail">
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

      <!-- 右侧抽屉：点击行展示订单详情（与退款订单同款） -->
      <transition name="slide-left">
        <div v-if="detailVisible" class="detail-panel">
          <div class="detail-header">
            <span class="detail-title">订单详情</span>
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
            <div class="detail-row"><span class="k">快递公司</span><span class="v">{{ currentRow.logistics_company || '—' }}</span></div>
            <div class="detail-row"><span class="k">运单号</span><span class="v">{{ currentRow.logistics_no || '—' }}<template v-if="currentRow.logistics_no_2"> / {{ currentRow.logistics_no_2 }}</template></span></div>
            <div class="detail-row"><span class="k">运费</span><span class="v">¥{{ fmt(currentRow.freight) }}</span></div>
            <div class="detail-row"><span class="k">收货地址</span><span class="v">{{ currentRow.receiver_address || '—' }}</span></div>
            <div class="detail-row"><span class="k">备注</span><span class="v">{{ currentRow.remark || '—' }}</span></div>
          </div>
        </div>
      </transition>
    </div>
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

// ==================== 右侧抽屉：订单详情（与退款订单同款） ====================
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
