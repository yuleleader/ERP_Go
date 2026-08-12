<template>
  <div class="account-withdrawal">
    <div class="layout-container">
      <div class="left-panel">
        <div class="panel-header">
          <h3>网店列表</h3>
        </div>
        <div class="search-box">
          <el-input
            v-model="shopKeyword"
            placeholder="搜索网店ID/名称/创建人"
            clearable
            @keyup.enter="searchShops"
            @clear="searchShops"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" @click="searchShops">搜索</el-button>
        </div>
        <div class="shop-list">
          <div v-for="group in shopGroups" :key="group.creator" class="shop-group">
            <div class="group-header">
              <span class="group-icon">👤</span>
              <span class="group-name">{{ group.creator_name }}</span>
              <span class="group-count">({{ group.shops.length }})</span>
            </div>
            <div class="group-shops">
              <div
                v-for="shop in group.shops"
                :key="shop.shop_id"
                class="shop-item"
                :class="{ active: selectedShop?.shop_id === shop.shop_id }"
                @click="selectShop(shop)"
              >
                <span class="shop-id">{{ shop.shop_id }}</span>
                <span class="shop-name">{{ shop.shop_name }}</span>
              </div>
            </div>
          </div>
          <div v-if="shopGroups.length === 0" class="empty-list">
            <el-empty description="暂无网店数据" />
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div v-if="!selectedShop" class="empty-state">
          <el-empty description="请在左侧选择网店" />
        </div>

        <template v-else>
          <div class="top-bar">
            <div class="shop-info">
              <span class="info-label">平台：</span>
              <span class="info-value">{{ selectedShop.shop_name }}</span>
              <span class="info-divider">|</span>
              <span class="info-label">网店ID：</span>
              <span class="info-value">{{ selectedShop.shop_id }}</span>
            </div>
            <div class="top-actions">
              <el-button v-if="canAdd" type="primary" @click="openAddDialog">
                <el-icon><Plus /></el-icon>新增提现记录
              </el-button>
              <el-button type="success" @click="handleExport">
                <el-icon><Download /></el-icon>导出数据
              </el-button>
            </div>
          </div>

          <el-card class="filter-card">
            <el-form :inline="true" :model="filterForm" class="filter-form">
              <el-form-item label="提现日期">
                <el-date-picker v-model="filterForm.withdraw_date_start" type="date" placeholder="开始日期"
                  format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
                <span class="date-divider">至</span>
                <el-date-picker v-model="filterForm.withdraw_date_end" type="date" placeholder="结束日期"
                  format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="录入人">
                <el-input v-model="filterForm.create_operator_name" placeholder="搜索录入人" clearable />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleSearch">查询</el-button>
                <el-button @click="resetFilter">重置</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <div class="summary-bar">
            <span>记录总数：<strong>{{ pagination.total }}</strong> 条</span>
            <span>提现总金额：<strong class="amount">¥{{ summaryTotalAmount.toFixed(2) }}</strong></span>
          </div>

          <el-card class="data-card">
            <el-table :data="recordList" border stripe>
              <el-table-column prop="withdraw_date" label="提现日期" width="120" />
              <el-table-column prop="withdraw_amount" label="提现金额(元)" width="140">
                <template #default="{ row }">
                  <span class="amount-text">¥{{ row.withdraw_amount.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="remark" label="备注" show-overflow-tooltip />
              <el-table-column prop="create_operator_name" label="创建人" width="100" />
              <el-table-column prop="create_time" label="创建时间" width="180">
                <template #default="{ row }">{{ formatDateTime(row.create_time) }}</template>
              </el-table-column>
              <el-table-column prop="update_operator_name" label="最后修改人" width="120" />
              <el-table-column prop="update_time" label="最后修改时间" width="180">
                <template #default="{ row }">{{ formatDateTime(row.update_time) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" @click="viewRecord(row)">详情</el-button>
                  <el-button v-if="canEdit" size="small" type="primary" @click="openEditDialog(row)">编辑</el-button>
                  <el-button v-if="userStore.role === 'boss' && canDelete" size="small" type="danger" @click="handleDelete(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="recordList.length === 0" class="empty-tip">
              该网店暂无提现记录，可点击上方新增按钮创建记录
            </div>
          </el-card>

          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.page_size"
              :total="pagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </template>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑提现记录' : '新增提现记录'" width="500px" @close="closeDialog">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="网店ID"><el-input :value="formData.shop_id" disabled /></el-form-item>
        <el-form-item label="提现日期" prop="withdraw_date">
          <el-date-picker v-model="formData.withdraw_date" type="date" placeholder="选择日期"
            format="YYYY-MM-DD" value-format="YYYY-MM-DD"
            :disabled-date="disabledFutureDate" style="width:100%" />
        </el-form-item>
        <el-form-item label="提现金额" prop="withdraw_amount">
          <el-input-number v-model="formData.withdraw_amount" :min="0.01" :precision="2" :step="0.01"
            placeholder="请输入提现金额" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="formData.remark" type="textarea" :rows="3"
            placeholder="可填写手续费、提现批次、营收周期等信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveRecord">保存</el-button>
        <el-button v-if="!isEdit" type="success" @click="saveAndContinue">保存并继续新增</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" title="提现记录详情" width="500px">
      <div v-if="currentRecord" class="detail-content">
        <div class="detail-row"><span class="detail-label">网店ID：</span><span class="detail-value">{{ currentRecord.shop_id }}</span></div>
        <div class="detail-row"><span class="detail-label">提现日期：</span><span class="detail-value">{{ currentRecord.withdraw_date }}</span></div>
        <div class="detail-row"><span class="detail-label">提现金额：</span><span class="detail-value amount">¥{{ currentRecord.withdraw_amount.toFixed(2) }}</span></div>
        <div class="detail-row"><span class="detail-label">备注：</span><span class="detail-value">{{ currentRecord.remark || '-' }}</span></div>
        <div class="detail-row"><span class="detail-label">创建人：</span><span class="detail-value">{{ currentRecord.create_operator_name }}</span></div>
        <div class="detail-row"><span class="detail-label">创建时间：</span><span class="detail-value">{{ formatDateTime(currentRecord.create_time) }}</span></div>
        <div class="detail-row"><span class="detail-label">最后修改人：</span><span class="detail-value">{{ currentRecord.update_operator_name || '-' }}</span></div>
        <div class="detail-row"><span class="detail-label">最后修改时间：</span><span class="detail-value">{{ formatDateTime(currentRecord.update_time) }}</span></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'AccountWithdrawal' })
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Download } from '@element-plus/icons-vue'
import { withdrawApi } from '@/api'
import { formatDate, formatDateTime } from '@/utils/format'
import { useUserStore } from '@/store/user'
import { checkDataPerm } from '@/utils/dataPerm'

const userStore = useUserStore()
const canAdd = computed(() => checkDataPerm(userStore.userInfo, '/account-withdrawal', 'add'))
const canEdit = computed(() => checkDataPerm(userStore.userInfo, '/account-withdrawal', 'edit'))
const canDelete = computed(() => checkDataPerm(userStore.userInfo, '/account-withdrawal', 'delete'))

const shopKeyword = ref('')
const shopGroups = ref([])
const selectedShop = ref(null)

const filterForm = reactive({
  withdraw_date_start: '',
  withdraw_date_end: '',
  create_operator_name: ''
})

const pagination = reactive({ page: 1, page_size: 10, total: 0 })
const recordList = ref([])
const summaryTotalAmount = ref(0)

const dialogVisible = ref(false)
const detailDialogVisible = ref(false)
const isEdit = ref(false)
const currentRecord = ref(null)
const formRef = ref(null)

const formData = reactive({
  shop_id: '',
  withdraw_date: '',
  withdraw_amount: null,
  remark: ''
})

const formRules = {
  withdraw_date: [{ required: true, message: '请选择提现日期', trigger: 'change' }],
  withdraw_amount: [{ required: true, message: '请输入提现金额', trigger: 'blur' }]
}

const searchShops = async () => {
  try {
    const res = await withdrawApi.getWithdrawShops(shopKeyword.value)
    if (res.code === 200) shopGroups.value = res.data
  } catch { ElMessage.error('获取网店列表失败') }
}

const selectShop = (shop) => {
  selectedShop.value = shop
  formData.shop_id = shop.shop_id
  pagination.page = 1
  loadRecords()
}

const loadRecords = async () => {
  if (!selectedShop.value) return
  try {
    const params = { page: pagination.page, page_size: pagination.page_size, ...filterForm }
    const res = await withdrawApi.getWithdrawRecords(selectedShop.value.shop_id, params)
    if (res.code === 200) {
      recordList.value = res.data.list
      pagination.total = res.data.total
      summaryTotalAmount.value = res.data.total_amount || 0
    }
  } catch { ElMessage.error('获取提现记录失败') }
}

const handleSearch = () => { pagination.page = 1; loadRecords() }
const resetFilter = () => {
  filterForm.withdraw_date_start = ''
  filterForm.withdraw_date_end = ''
  filterForm.amount_min = null
  filterForm.amount_max = null
  filterForm.create_operator_name = ''
  pagination.page = 1
  loadRecords()
}
const handleSizeChange = (size) => { pagination.page_size = size; pagination.page = 1; loadRecords() }
const handleCurrentChange = (page) => { pagination.page = page; loadRecords() }

const openAddDialog = () => {
  isEdit.value = false
  currentRecord.value = null
  formData.shop_id = selectedShop.value?.shop_id || ''
  formData.withdraw_date = formatDate(new Date())
  formData.withdraw_amount = null
  formData.remark = ''
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  currentRecord.value = row
  formData.shop_id = row.shop_id
  formData.withdraw_date = row.withdraw_date
  formData.withdraw_amount = row.withdraw_amount
  formData.remark = row.remark || ''
  dialogVisible.value = true
}

const viewRecord = (row) => { currentRecord.value = row; detailDialogVisible.value = true }
const closeDialog = () => { dialogVisible.value = false; formRef.value?.resetFields() }
const disabledFutureDate = (time) => time.getTime() > Date.now()

const doSave = async () => {
  await formRef.value.validate()
  const payload = {
    shop_id: formData.shop_id,
    withdraw_date: formData.withdraw_date,
    withdraw_amount: formData.withdraw_amount,
    remark: formData.remark
  }

  if (isEdit.value) {
    await withdrawApi.updateWithdrawRecord(currentRecord.value.id, payload)
    ElMessage.success('编辑成功')
  } else {
    const res = await withdrawApi.createWithdrawRecord(payload)
    if (res.data?.exists_same_day) {
      ElMessage.warning('该网店当日已存在提现记录，请确认是否重复登记')
    }
    ElMessage.success('新增成功')
  }
}

const saveRecord = async () => {
  try {
    await doSave()
    closeDialog()
    loadRecords()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

const saveAndContinue = async () => {
  try {
    await doSave()
    formData.withdraw_amount = null
    formData.remark = ''
    loadRecords()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该提现记录？操作将留存日志，数据无法恢复！', '确认删除', { type: 'warning' })
    await withdrawApi.deleteWithdrawRecord(row.id)
    ElMessage.success('删除成功')
    loadRecords()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('删除失败')
  }
}

const handleExport = async () => {
    if (!selectedShop.value) return
    try {
      const res = await withdrawApi.exportWithdrawRecords(selectedShop.value.shop_id, filterForm)
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `网店【${selectedShop.value.shop_name}】提现流水.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    } catch { ElMessage.error('导出失败') }
  }

onMounted(() => { searchShops() })
</script>

<style scoped>
.account-withdrawal { height: 100%; display: flex; }
.layout-container { display: flex; width: 100%; height: 100%; }

.left-panel {
  width: 320px; background: #f5f7fa; border-right: 1px solid #e4e7ed;
  display: flex; flex-direction: column;
}
.panel-header { padding: 20px; border-bottom: 1px solid #e4e7ed; background: #fff; }
.panel-header h3 { margin: 0; font-size: 16px; font-weight: 600; }
.search-box { padding: 15px; display: flex; gap: 10px; background: #fff; border-bottom: 1px solid #e4e7ed; }
.search-box .el-input { flex: 1; }
.shop-list { flex: 1; overflow-y: auto; padding: 10px; }
.shop-group { margin-bottom: 16px; }
.group-header {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; font-size: 13px; font-weight: 600;
  color: #409eff; background: #ecf5ff; border-radius: 4px;
}
.group-icon { font-size: 14px; }
.group-name { flex: 1; }
.group-count { font-size: 12px; color: #909399; font-weight: 400; }
.group-shops { padding-left: 20px; margin-top: 8px; }
.shop-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; margin-bottom: 4px; background: #fff; border-radius: 4px;
  cursor: pointer; transition: all 0.2s; border-left: 3px solid transparent;
}
.shop-item:hover { background: #f5f7fa; border-left-color: #b3d8ff; }
.shop-item.active { background: #ecf5ff; border-left-color: #409eff; }
.shop-item.active .shop-id { color: #409eff; }
.shop-id { font-size: 14px; font-weight: 600; color: #303133; flex-shrink: 0; }
.shop-name { font-size: 13px; color: #606266; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-list { padding: 40px 20px; }

.right-panel { flex: 1; padding: 20px; overflow-y: auto; background: #fff; }
.empty-state { height: 100%; display: flex; align-items: center; justify-content: center; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.shop-info { display: flex; align-items: center; gap: 8px; }
.info-label { font-size: 14px; color: #606266; }
.info-value { font-size: 16px; font-weight: 600; color: #303133; }
.info-divider { color: #dcdfe6; }
.top-actions { display: flex; gap: 10px; }

.filter-card { margin-bottom: 15px; }
.filter-form { display: flex; flex-wrap: wrap; gap: 15px; align-items: center; }
.filter-form .el-form-item { margin-bottom: 5px; }
.date-divider { margin: 0 8px; color: #909399; }

.summary-bar {
  display: flex; gap: 30px; margin-bottom: 15px;
  padding: 12px 20px; background: #f5f7fa; border-radius: 6px;
  font-size: 14px; color: #606266;
}
.summary-bar .amount { color: #e6a23c; }
.data-card { margin-bottom: 15px; }
.amount-text { color: #e6a23c; font-weight: 600; }
.empty-tip { text-align: center; padding: 40px; color: #909399; font-size: 14px; }
.pagination-bar { display: flex; justify-content: flex-end; }

.detail-content { padding: 10px 0; }
.detail-row { display: flex; padding: 10px 0; border-bottom: 1px dashed #ebeef5; }
.detail-row:last-child { border-bottom: none; }
.detail-label { width: 100px; font-weight: 500; color: #606266; }
.detail-value { flex: 1; color: #303133; }
.detail-value.amount { color: #e6a23c; font-weight: 600; }
</style>