<template>
  <div class="non-trade-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>非交易收入/支出录入</span>
          <div class="header-right">
            <span class="sub-tip">每人维护自己的数据</span>
            <el-button type="primary" @click="openCreate">
              <el-icon style="margin-right: 4px"><Plus /></el-icon>新增录入
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选区 -->
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">类型：</span>
          <el-select v-model="filters.transType" placeholder="全部" clearable style="width: 120px" @change="fetchList">
            <el-option label="收入" value="income" />
            <el-option label="支出" value="expense" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">账务代码：</span>
          <el-select v-model="filters.codeId" placeholder="全部" clearable filterable style="width: 200px" @change="fetchList">
            <el-option v-for="c in codes" :key="c.id" :label="`${c.code} ${c.name}`" :value="c.id" />
          </el-select>
        </div>
        <div class="filter-item" v-if="isBoss">
          <span class="filter-label">录入人：</span>
          <el-select v-model="filters.createdBy" placeholder="全部" clearable style="width: 140px" @change="fetchList">
            <el-option v-for="u in userOptions" :key="u.username" :label="u.label" :value="u.username" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">录入时间：</span>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </div>
        <div class="filter-item">
          <span class="filter-label">关键词：</span>
          <el-input v-model="filters.keyword" placeholder="代码/名称/备注" clearable style="width: 160px" @keyup.enter="fetchList" />
        </div>
        <el-button type="primary" @click="fetchList">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
      </div>

      <!-- 汇总 -->
      <div class="totals-bar">
        <span>共 <b>{{ totalCount }}</b> 笔</span>
        <span>收入合计 <b class="income">¥{{ fmt(incomeTotal) }}</b></span>
        <span>支出合计 <b class="expense">¥{{ fmt(expenseTotal) }}</b></span>
        <span>结余 <b :class="netTotal >= 0 ? 'income' : 'expense'">¥{{ fmt(netTotal) }}</b></span>
      </div>

      <!-- 表格 -->
      <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="560">
        <el-table-column label="序号" width="62" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="账务代码" min-width="170">
          <template #default="{ row }">
            <span class="code-text">{{ row.code }}</span>
            <span class="code-name">{{ row.code_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.trans_type === 'income' ? 'success' : 'danger'" size="small">{{ row.trans_type_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">
            <span :class="row.trans_type === 'income' ? 'amount-income' : 'amount-expense'">
              {{ row.trans_type === 'income' ? '+' : '-' }}¥{{ fmt(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="shop_name" label="关联网店" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.shop_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '—' }}</template>
        </el-table-column>
        <el-table-column prop="created_by_name" label="录入人" width="100" align="center" v-if="isBoss" />
        <el-table-column prop="create_time" label="录入时间" width="150" align="center">
          <template #default="{ row }">{{ row.create_time || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑收支记录' : '新增收支记录'" width="520px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" label-width="90px">
        <el-form-item label="账务代码" required>
          <el-select v-model="form.code_id" placeholder="请选择账务代码" filterable style="width: 100%" @change="onCodeChange">
            <el-option-group label="非交易支出">
              <el-option v-for="c in expenseCodes" :key="c.id" :label="`${c.code} ${c.name}`" :value="c.id" />
            </el-option-group>
            <el-option-group label="非交易收入">
              <el-option v-for="c in incomeCodes" :key="c.id" :label="`${c.code} ${c.name}`" :value="c.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="收入/支出" required>
          <el-radio-group v-model="form.trans_type">
            <el-radio-button value="expense">支出</el-radio-button>
            <el-radio-button value="income">收入</el-radio-button>
          </el-radio-group>
          <span v-if="selectedCode" class="code-type-hint">当前代码为「{{ selectedCode.code_type_text }}」</span>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="form.amount" :min="0" :precision="2" :step="10" style="width: 200px" />
        </el-form-item>
        <el-form-item label="关联网店">
          <el-select v-model="form.shop_id" placeholder="可选，仅限自己创建的网店" clearable filterable style="width: 100%">
            <el-option v-for="s in myShops" :key="s.shop_id" :label="s.shop_name" :value="s.shop_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="500" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'NonTradeTransactions' })
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import {
  getAccountingCodes,
  getMyShops,
  getNonTradeTransactions,
  createNonTradeTransaction,
  updateNonTradeTransaction,
  deleteNonTradeTransaction
} from '@/api/nonTrade'
import { getUsers } from '@/api/user'

const userStore = useUserStore()
const isBoss = computed(() => userStore.isBoss)

const loading = ref(false)
const items = ref([])
const totalCount = ref(0)
const incomeTotal = ref(0)
const expenseTotal = ref(0)
const netTotal = computed(() => incomeTotal.value - expenseTotal.value)
const dateRange = ref(null)
const filters = reactive({ transType: '', codeId: null, createdBy: '', keyword: '' })

const codes = ref([])
const incomeCodes = computed(() => codes.value.filter((c) => c.code_type === 'income'))
const expenseCodes = computed(() => codes.value.filter((c) => c.code_type === 'expense'))
const selectedCode = computed(() => codes.value.find((c) => c.id === form.code_id) || null)
const myShops = ref([])
const userOptions = ref([])

function fmt(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function fetchCodes() {
  try {
    const res = await getAccountingCodes()
    codes.value = res.items || []
  } catch (e) {
    /* 忽略 */
  }
}

async function fetchMyShops() {
  try {
    const res = await getMyShops()
    myShops.value = res.items || []
  } catch (e) {
    /* 忽略 */
  }
}

async function fetchUsers() {
  try {
    const res = await getUsers({})
    const list = res || []
    userOptions.value = list.map((u) => ({ username: u.username, label: `${u.real_name || u.username}（${u.username}）` }))
  } catch (e) {
    /* 忽略 */
  }
}

async function fetchList() {
  loading.value = true
  try {
    const params = {}
    if (filters.transType) params.trans_type = filters.transType
    if (filters.codeId) params.code_id = filters.codeId
    if (filters.createdBy) params.created_by = filters.createdBy
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await getNonTradeTransactions(params)
    items.value = res.items || []
    totalCount.value = res.total || 0
    incomeTotal.value = items.value.filter((i) => i.trans_type === 'income').reduce((s, i) => s + Number(i.amount || 0), 0)
    expenseTotal.value = items.value.filter((i) => i.trans_type === 'expense').reduce((s, i) => s + Number(i.amount || 0), 0)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  filters.transType = ''
  filters.codeId = null
  filters.createdBy = ''
  filters.keyword = ''
  dateRange.value = null
  fetchList()
}

// ==================== 新增/编辑 ====================
const dialogVisible = ref(false)
const formRef = ref(null)
const saving = ref(false)
const form = reactive({ id: null, code_id: null, shop_id: '', trans_type: 'expense', amount: 0, remark: '' })

function onCodeChange(id) {
  const c = codes.value.find((x) => x.id === id)
  if (c) form.trans_type = c.code_type
}

function openCreate() {
  Object.assign(form, { id: null, code_id: null, shop_id: '', trans_type: 'expense', amount: 0, remark: '' })
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    code_id: row.code_id,
    shop_id: row.shop_id || '',
    trans_type: row.trans_type,
    amount: Number(row.amount || 0),
    remark: row.remark || ''
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.code_id) {
    ElMessage.warning('请选择账务代码')
    return
  }
  if (form.amount === null || form.amount === undefined || form.amount < 0) {
    ElMessage.warning('请输入正确的金额')
    return
  }
  saving.value = true
  try {
    const payload = {
      code_id: form.code_id,
      shop_id: form.shop_id || '',
      trans_type: form.trans_type,
      amount: form.amount,
      remark: form.remark || ''
    }
    if (form.id) {
      await updateNonTradeTransaction(form.id, payload)
      ElMessage.success('已保存')
    } else {
      await createNonTradeTransaction(payload)
      ElMessage.success('已录入')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除该笔收支记录（${row.code_name} ${row.trans_type_text} ¥${row.amount}）？`, '删除确认', { type: 'warning' })
  try {
    await deleteNonTradeTransaction(row.id)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  fetchCodes()
  fetchMyShops()
  if (isBoss.value) fetchUsers()
  fetchList()
})
</script>

<style scoped>
.non-trade-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sub-tip {
  color: #909399;
  font-size: 12px;
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
}

.totals-bar b {
  color: #409eff;
}

.totals-bar b.income {
  color: #67c23a;
}

.totals-bar b.expense {
  color: #f56c6c;
}

.code-text {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #409eff;
  margin-right: 6px;
}

.code-name {
  color: #606266;
}

.amount-income {
  color: #67c23a;
  font-weight: 600;
}

.amount-expense {
  color: #f56c6c;
  font-weight: 600;
}

.code-type-hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
