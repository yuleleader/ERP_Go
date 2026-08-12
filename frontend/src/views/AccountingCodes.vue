<template>
  <div class="accounting-codes-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>账务代码管理（非交易收入/支出类型）</span>
          <el-button v-if="canAdd" type="primary" @click="openCreate">
            <el-icon style="margin-right: 4px"><Plus /></el-icon>新增账务代码
          </el-button>
        </div>
      </template>

      <!-- 类型统计 -->
      <div class="stat-line">
        <el-tag type="success">非交易收入 {{ incomeCount }} 个</el-tag>
        <el-tag type="danger">非交易支出 {{ expenseCount }} 个</el-tag>
        <span class="tip-text">账务代码由系统自动生成：收入 SR001…、支出 ZC001…（递增）</span>
      </div>

      <el-table :data="items" v-loading="loading" border style="width: 100%" max-height="560">
        <el-table-column label="序号" width="65" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column prop="code" label="账务代码" width="120" align="center">
          <template #default="{ row }"><span class="code-text">{{ row.code }}</span></template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="code_type_text" label="类型" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="row.code_type === 'income' ? 'success' : 'danger'" size="small">{{ row.code_type_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '—' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" align="center">
          <template #default="{ row }">{{ row.created_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button v-if="canEdit" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="canDelete" link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑账务代码' : '新增账务代码'" width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：买水、广告费、佣金、平台补贴等" maxlength="100" />
        </el-form-item>
        <el-form-item label="类型" prop="code_type">
          <el-radio-group v-model="form.code_type">
            <el-radio-button value="expense">非交易支出</el-radio-button>
            <el-radio-button value="income">非交易收入</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="选填" />
        </el-form-item>
        <el-form-item v-if="form.id">
          <span class="code-preview">账务代码：{{ form.code }}（自动生成，不可修改）</span>
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
defineOptions({ name: 'AccountingCodes' })
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { checkDataPerm } from '@/utils/dataPerm'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getAccountingCodes, createAccountingCode, updateAccountingCode, deleteAccountingCode } from '@/api/nonTrade'

const userStore = useUserStore()
const canAdd = computed(() => checkDataPerm(userStore.userInfo, '/accounting-codes', 'add'))
const canEdit = computed(() => checkDataPerm(userStore.userInfo, '/accounting-codes', 'edit'))
const canDelete = computed(() => checkDataPerm(userStore.userInfo, '/accounting-codes', 'delete'))

const loading = ref(false)
const items = ref([])
const incomeCount = computed(() => items.value.filter((i) => i.code_type === 'income').length)
const expenseCount = computed(() => items.value.filter((i) => i.code_type === 'expense').length)

async function fetchList() {
  loading.value = true
  try {
    const res = await getAccountingCodes()
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

// ==================== 新增/编辑 ====================
const dialogVisible = ref(false)
const formRef = ref(null)
const saving = ref(false)
const form = reactive({ id: null, code: '', name: '', code_type: 'expense', remark: '' })
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

function openCreate() {
  Object.assign(form, { id: null, code: '', name: '', code_type: 'expense', remark: '' })
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, { id: row.id, code: row.code, name: row.name, code_type: row.code_type, remark: row.remark })
  dialogVisible.value = true
}

async function save() {
  if (!form.name || !form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name.trim(), code_type: form.code_type, remark: form.remark || '' }
    if (form.id) {
      await updateAccountingCode(form.id, payload)
      ElMessage.success('已保存')
    } else {
      await createAccountingCode(payload)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// ==================== 删除 ====================
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除账务代码「${row.code} ${row.name}」？`, '删除确认', { type: 'warning' })
  try {
    await deleteAccountingCode(row.id)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.accounting-codes-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-line {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.tip-text {
  color: #909399;
  font-size: 12px;
}

.code-text {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #409eff;
}

.code-preview {
  color: #909399;
  font-size: 13px;
}
</style>
