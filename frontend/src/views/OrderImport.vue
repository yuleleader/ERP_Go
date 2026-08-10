<template>
  <div class="order-import-container">
    <!-- 顶部操作卡片 -->
    <el-card class="action-card">
      <div class="action-bar">
        <div class="action-left">
          <span class="action-title">订单数据导入</span>
          <span class="action-sub">Excel → 临时表 → 勾选审核 → 合并正式订单表（合并时自动生成追溯码）</span>
        </div>
        <div class="action-right">
          <el-button type="success" plain @click="downloadTemplate">
            <el-icon style="margin-right: 4px"><Download /></el-icon>下载模板
          </el-button>
          <el-upload
            :show-file-list="false"
            :http-request="handleUpload"
            accept=".xlsx,.xls"
            :disabled="uploading"
          >
            <el-button type="primary" :loading="uploading">
              <el-icon style="margin-right: 4px"><Upload /></el-icon>{{ uploading ? '导入中…' : '上传 Excel 导入' }}
            </el-button>
          </el-upload>
        </div>
      </div>
      <el-alert type="info" :closable="false" class="tip-alert">
        <template #title>
          导入说明：先下载模板填写（含案例数据供参考，以"示例"开头的行导入时自动跳过）；上传后数据进入临时表，
          系统自动逐行检查异常并提示；仅<strong>无异常</strong>的订单可勾选审核合并到正式订单表，异常订单可点击
          「编辑」修正后再次审核。
        </template>
      </el-alert>
    </el-card>

    <!-- 列表卡片 -->
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>待审核导入数据（共 <b>{{ totalCount }}</b> 条）</span>
        </div>
      </template>

      <!-- 筛选区 -->
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">状态：</span>
          <el-select v-model="filters.abnormal" placeholder="全部" clearable style="width: 140px" @change="fetchList">
            <el-option label="全部" value="" />
            <el-option label="有异常" value="1" />
            <el-option label="无异常" value="0" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">批次号：</span>
          <el-input v-model="filters.batchNo" placeholder="批次号" clearable style="width: 180px" @keyup.enter="fetchList" />
        </div>
        <div class="filter-item">
          <span class="filter-label">关键词：</span>
          <el-input v-model="filters.keyword" placeholder="平台订单号/商品名称" clearable style="width: 200px" @keyup.enter="fetchList" />
        </div>
        <el-button type="primary" @click="fetchList">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
        <div class="filter-spacer" />
        <el-button type="danger" plain :disabled="!selectedIds.length" @click="handleBatchDelete">
          批量删除（{{ selectedIds.length }}）
        </el-button>
        <el-button type="success" :disabled="!selectedIds.length" @click="handleMerge">
          审核合并（{{ selectedIds.length }}）
        </el-button>
      </div>

      <!-- 表格 -->
      <el-table
        ref="tableRef"
        :data="items"
        v-loading="loading"
        border
        style="width: 100%"
        max-height="640"
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <el-table-column type="selection" width="48" align="center" :selectable="rowSelectable" />
        <el-table-column label="序号" width="58" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column prop="platform_order_no" label="平台订单号" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="pno-text">{{ row.platform_order_no || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="shop_name" label="网店名称" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.shop_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="product_name" label="商品名称" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.product_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="sales_amount" label="销售金额" width="100" align="right">
          <template #default="{ row }">{{ row.sales_amount !== '' ? '¥' + row.sales_amount : '—' }}</template>
        </el-table-column>
        <el-table-column prop="freight" label="运费" width="90" align="right">
          <template #default="{ row }">{{ row.freight !== '' ? '¥' + row.freight : '—' }}</template>
        </el-table-column>
        <el-table-column prop="shipping_status_text" label="发货状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.shipping_status)" size="small">{{ row.shipping_status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="produce_status_text" label="生产状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="produceTagType(row.produce_status)" size="small">{{ row.produce_status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="logistics_no" label="物流单号" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.logistics_no || '—' }}</template>
        </el-table-column>
        <el-table-column prop="order_time" label="下单时间" width="120" align="center">
          <template #default="{ row }">{{ row.order_time || '—' }}</template>
        </el-table-column>
        <el-table-column prop="imported_by_name" label="导入人" width="90" align="center" v-if="isBoss">
          <template #default="{ row }">{{ row.imported_by_name }}</template>
        </el-table-column>
        <el-table-column prop="import_time" label="导入时间" width="150" align="center">
          <template #default="{ row }">{{ row.import_time || '—' }}</template>
        </el-table-column>
        <!-- 异常提示列 -->
        <el-table-column label="异常提示" min-width="220">
          <template #default="{ row }">
            <div v-if="row.errors && row.errors.length" class="error-list">
              <el-tag v-for="(e, i) in row.errors" :key="i" type="danger" size="small" class="error-tag">{{ e }}</el-tag>
            </div>
            <el-tag v-else type="success" size="small" effect="plain">无异常</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" title="编辑临时订单" width="640px" :close-on-click-modal="false">
      <el-alert v-if="editForm.errors && editForm.errors.length" type="warning" :closable="false" class="edit-alert">
        <template #title>
          当前存在异常：{{ editForm.errors.join('；') }}。保存后需再次审核通过才能合并。
        </template>
      </el-alert>
      <el-form ref="editFormRef" :model="editForm" label-width="100px" class="edit-form">
        <div class="form-row">
          <el-form-item label="平台订单号" required>
            <el-input v-model="editForm.platform_order_no" placeholder="必填" />
          </el-form-item>
          <el-form-item label="商品名称">
            <el-input v-model="editForm.product_name" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="网店名称">
            <el-input v-model="editForm.shop_name" placeholder="与网店信息中的名称一致" />
          </el-form-item>
          <el-form-item label="网店账号">
            <el-input v-model="editForm.shop_account" placeholder="与网店信息中的账号一致" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="销售金额">
            <el-input v-model="editForm.sales_amount" placeholder="数字" />
          </el-form-item>
          <el-form-item label="运费">
            <el-input v-model="editForm.freight" placeholder="数字，可空" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="发货状态">
            <el-select v-model="editForm.shipping_status" style="width: 100%">
              <el-option label="待发货" value="pending" />
              <el-option label="已发货" value="shipped" />
              <el-option label="虚拟发货" value="virtual" />
              <el-option label="已退货/退款" value="refunded" />
            </el-select>
          </el-form-item>
          <el-form-item label="生产状态">
            <el-select v-model="editForm.produce_status" style="width: 100%">
              <el-option label="未生产" value="unproduce" />
              <el-option label="生产中" value="producing" />
              <el-option label="生产完成" value="produced" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="快递公司">
            <el-input v-model="editForm.logistics_company" />
          </el-form-item>
          <el-form-item label="运单号">
            <el-input v-model="editForm.logistics_no" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="下单时间">
            <el-date-picker v-model="editForm.order_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="选择下单时间" style="width: 100%" />
          </el-form-item>
          <el-form-item label="发货时间">
            <el-date-picker v-model="editForm.shipping_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="可空" clearable style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="收货地址">
          <el-input v-model="editForm.receiver_address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="退款备注" :class="{ 'refund-required': editForm.shipping_status === 'refunded' }">
          <el-input v-model="editForm.refund_note" type="textarea" :rows="2" :placeholder="editForm.shipping_status === 'refunded' ? '已退货/退款订单必填' : '选填'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存（重新审核）</el-button>
      </template>
    </el-dialog>

    <!-- 合并确认对话框 -->
    <el-dialog v-model="mergeConfirmVisible" title="审核合并确认" width="560px">
      <div class="merge-summary">
        <div class="merge-stat">
          <span class="merge-num ok">{{ mergeOkCount }}</span>
          <span class="merge-label">无异常可合并</span>
        </div>
        <div class="merge-stat">
          <span class="merge-num bad">{{ mergeBadCount }}</span>
          <span class="merge-label">有异常不可合并</span>
        </div>
      </div>
      <div v-if="mergeBadItems.length" class="merge-bad-list">
        <div class="merge-bad-title">以下订单存在异常，无法合并（请先编辑修正后再审核）：</div>
        <div v-for="(it, i) in mergeBadItems" :key="i" class="merge-bad-item">
          <span class="merge-pno">{{ it.platform_order_no || '未填订单号' }}</span>
          <el-tag v-for="(e, j) in it.errors" :key="j" type="danger" size="small" class="error-tag">{{ e }}</el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="mergeConfirmVisible = false">取消</el-button>
        <el-button type="success" :loading="merging" :disabled="mergeOkCount === 0" @click="confirmMerge">
          合并 {{ mergeOkCount }} 条到正式订单表
        </el-button>
      </template>
    </el-dialog>

    <!-- 合并结果对话框 -->
    <el-dialog v-model="mergeResultVisible" title="合并结果" width="620px">
      <el-alert
        :type="mergeResult.failed ? 'warning' : 'success'"
        :closable="false"
        class="edit-alert"
      >
        <template #title>合并成功 {{ mergeResult.merged }} 条，失败 {{ mergeResult.failed }} 条</template>
      </el-alert>
      <div v-if="mergeResult.merged_items && mergeResult.merged_items.length" class="result-block">
        <div class="result-title">成功（已生成追溯码）：</div>
        <div v-for="(it, i) in mergeResult.merged_items" :key="i" class="result-item ok-item">
          <span class="merge-pno">{{ it.platform_order_no }}</span>
          <span class="result-order-id">→ {{ it.order_id }}</span>
        </div>
      </div>
      <div v-if="mergeResult.failed_items && mergeResult.failed_items.length" class="result-block">
        <div class="result-title">失败（已保留在临时表）：</div>
        <div v-for="(it, i) in mergeResult.failed_items" :key="i" class="result-item bad-item">
          <span class="merge-pno">{{ it.platform_order_no || '未填订单号' }}</span>
          <el-tag v-for="(e, j) in it.errors" :key="j" type="danger" size="small" class="error-tag">{{ e }}</el-tag>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="mergeResultVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'OrderImport' })
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import {
  downloadImportTemplate,
  importOrderExcel,
  getOrderImports,
  updateOrderImport,
  mergeOrderImports,
  deleteOrderImport,
  deleteBatchOrderImports
} from '@/api/orderImport'

const userStore = useUserStore()
const isBoss = computed(() => userStore.isBoss)

// ==================== 列表 ====================
const loading = ref(false)
const items = ref([])
const totalCount = ref(0)
const filters = reactive({ abnormal: '', batchNo: '', keyword: '' })

async function fetchList() {
  loading.value = true
  try {
    const params = {}
    if (filters.abnormal !== '') params.only_abnormal = filters.abnormal === '1'
    if (filters.batchNo.trim()) params.batch_no = filters.batchNo.trim()
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    const res = await getOrderImports(params)
    items.value = res.items || []
    totalCount.value = res.total || 0
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  filters.abnormal = ''
  filters.batchNo = ''
  filters.keyword = ''
  fetchList()
}

// ==================== 模板下载 ====================
function saveBlob(data, filename) {
  const url = window.URL.createObjectURL(new Blob([data]))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

async function downloadTemplate() {
  try {
    const res = await downloadImportTemplate()
    const today = new Date().toISOString().slice(0, 10)
    const fileName = `订单导入模板-${today}.xlsx`
    saveBlob(res.data, fileName)
    ElMessage.success('模板已下载（含列名与案例数据）')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '模板下载失败')
  }
}

// ==================== 上传导入 ====================
const uploading = ref(false)
async function handleUpload({ file }) {
  uploading.value = true
  try {
    const res = await importOrderExcel(file)
    ElMessage.success(res.message || '导入成功')
    fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '导入失败')
  } finally {
    uploading.value = false
  }
}

// ==================== 勾选 ====================
const selectedIds = ref([])
const selectedRows = ref([])

function rowSelectable(row) {
  // 有异常的行也可勾选（勾选后合并按钮会拦截并提示），方便"全选后只合并无异常的"
  return true
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
  selectedIds.value = rows.map((r) => r.id)
}

// ==================== 编辑 ====================
const editVisible = ref(false)
const editFormRef = ref(null)
const saving = ref(false)
const editForm = reactive({
  id: null,
  platform_order_no: '',
  shop_name: '',
  shop_account: '',
  product_name: '',
  sales_amount: '',
  freight: '',
  shipping_status: 'pending',
  produce_status: 'unproduce',
  logistics_company: '',
  logistics_no: '',
  receiver_address: '',
  remark: '',
  refund_note: '',
  order_time: '',
  shipping_time: '',
  errors: []
})

function openEdit(row) {
  Object.assign(editForm, {
    id: row.id,
    platform_order_no: row.platform_order_no,
    shop_name: row.shop_name,
    shop_account: row.shop_account,
    product_name: row.product_name,
    sales_amount: row.sales_amount,
    freight: row.freight,
    shipping_status: row.shipping_status,
    produce_status: row.produce_status,
    logistics_company: row.logistics_company,
    logistics_no: row.logistics_no,
    receiver_address: row.receiver_address,
    remark: row.remark,
    refund_note: row.refund_note,
    order_time: row.order_time || '',
    shipping_time: row.shipping_time || '',
    errors: row.errors || []
  })
  editVisible.value = true
}

async function saveEdit() {
  if (!editForm.platform_order_no || !editForm.platform_order_no.trim()) {
    ElMessage.warning('平台订单号不能为空')
    return
  }
  saving.value = true
  try {
    const payload = { ...editForm }
    delete payload.id
    delete payload.errors
    // 时间空串转空值
    ;['order_time', 'shipping_time'].forEach((k) => {
      if (!payload[k]) payload[k] = ''
    })
    const row = await updateOrderImport(editForm.id, payload)
    ElMessage.success('已保存并重新审核')
    editVisible.value = false
    if (row.errors && row.errors.length) {
      ElMessage.warning(`保存成功，但仍存在 ${row.errors.length} 项异常，需修正后才能合并`)
    } else {
      ElMessage.success('审核通过，无异常，可合并到正式订单表')
    }
    fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// ==================== 删除 ====================
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除临时订单「${row.platform_order_no || '未填订单号'}」？`, '删除确认', { type: 'warning' })
  try {
    await deleteOrderImport(row.id)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除勾选的 ${selectedIds.value.length} 条临时数据？`, '批量删除确认', { type: 'warning' })
  try {
    await deleteBatchOrderImports(selectedIds.value)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// ==================== 审核合并 ====================
const mergeConfirmVisible = ref(false)
const merging = ref(false)
const mergeBadItems = ref([])
const mergeOkIds = ref([])
const mergeOkCount = computed(() => mergeOkIds.value.length)
const mergeBadCount = computed(() => mergeBadItems.value.length)

function handleMerge() {
  const okIds = []
  const bad = []
  selectedRows.value.forEach((row) => {
    if (row.errors && row.errors.length) {
      bad.push({ id: row.id, platform_order_no: row.platform_order_no, errors: row.errors })
    } else {
      okIds.push(row.id)
    }
  })
  mergeOkIds.value = okIds
  mergeBadItems.value = bad
  mergeConfirmVisible.value = true
}

async function confirmMerge() {
  merging.value = true
  try {
    const res = await mergeOrderImports(mergeOkIds.value)
    mergeConfirmVisible.value = false
    mergeResult.value = res
    mergeResultVisible.value = true
    fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '合并失败')
  } finally {
    merging.value = false
  }
}

const mergeResultVisible = ref(false)
const mergeResult = ref({ merged: 0, failed: 0, merged_items: [], failed_items: [] })

// ==================== 样式辅助 ====================
function statusTagType(status) {
  return { pending: 'warning', shipped: 'success', virtual: 'info', refunded: 'danger' }[status] || 'info'
}
function produceTagType(status) {
  return { unproduce: 'warning', producing: 'primary', produced: 'success' }[status] || 'info'
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.order-import-container {
  padding: 16px;
}

.action-card {
  margin-bottom: 14px;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.action-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-right: 10px;
}

.action-sub {
  font-size: 12px;
  color: #909399;
}

.action-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tip-alert {
  margin-bottom: 0;
}

.list-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header b {
  color: #409eff;
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

.pno-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.error-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.error-tag {
  margin-right: 4px;
  margin-bottom: 2px;
  white-space: normal;
  height: auto;
  line-height: 1.4;
  padding: 1px 6px;
}

.edit-alert {
  margin-bottom: 12px;
}

.edit-form .form-row {
  display: flex;
  gap: 12px;
}

.edit-form .form-row .el-form-item {
  flex: 1;
}

.refund-required :deep(.el-form-item__label) {
  color: #f56c6c;
  font-weight: 600;
}

/* 合并确认 */
.merge-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 14px;
}

.merge-stat {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.merge-num {
  font-size: 28px;
  font-weight: 700;
}

.merge-num.ok {
  color: #67c23a;
}

.merge-num.bad {
  color: #f56c6c;
}

.merge-label {
  color: #909399;
  font-size: 13px;
}

.merge-bad-list {
  max-height: 240px;
  overflow-y: auto;
  border-top: 1px dashed #ebeef5;
  padding-top: 10px;
}

.merge-bad-title {
  color: #f56c6c;
  font-size: 13px;
  margin-bottom: 8px;
}

.merge-bad-item {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px 0;
}

.merge-pno {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #303133;
  min-width: 120px;
}

/* 合并结果 */
.result-block {
  margin-top: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.result-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}

.result-item {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 0;
}

.ok-item {
  color: #67c23a;
}

.bad-item {
  color: #f56c6c;
}

.result-order-id {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #409eff;
  word-break: break-all;
}
</style>
