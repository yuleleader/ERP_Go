<template>
  <div class="logistics-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>物流公司管理</span>
          <el-button type="primary" @click="showCreateDialog" v-if="canManage">
            新增物流公司
          </el-button>
        </div>
      </template>

      <el-table :data="companies" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="company_code" label="公司代码" width="120" />
        <el-table-column prop="company_name" label="公司名称" width="150" />
        <el-table-column prop="contact_person" label="联系人" width="120" />
        <el-table-column prop="contact_phone" label="联系电话" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" v-if="canManage">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editCompany(row)">
              编辑
            </el-button>
            <el-button link type="danger" size="small" @click="deleteCompany(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" @closed="resetForm">
      <el-form ref="companyFormRef" :model="companyForm" :rules="companyRules" label-width="120px">
        <el-form-item label="公司代码" prop="company_code">
          <el-input v-model="companyForm.company_code" placeholder="请输入公司代码" />
        </el-form-item>

        <el-form-item label="公司名称" prop="company_name">
          <el-input v-model="companyForm.company_name" placeholder="请输入公司名称" />
        </el-form-item>

        <el-form-item label="联系人">
          <el-input v-model="companyForm.contact_person" placeholder="请输入联系人" />
        </el-form-item>

        <el-form-item label="联系电话">
          <el-input v-model="companyForm.contact_phone" placeholder="请输入联系电话" />
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-select v-model="companyForm.status" placeholder="请选择状态">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCompany" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { getLogisticsCompanies, createLogisticsCompany, updateLogisticsCompany, deleteLogisticsCompany as deleteCompanyApi } from '@/api/logistics'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/format'

const userStore = useUserStore()

const loading = ref(false)
const companies = ref([])
const dialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const companyFormRef = ref(null)

const companyForm = reactive({
  company_code: '',
  company_name: '',
  contact_person: '',
  contact_phone: '',
  status: 'active'
})

const companyRules = {
  company_code: [{ required: true, message: '请输入公司代码', trigger: 'blur' }],
  company_name: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const currentCompany = ref(null)

const canManage = computed(() => ['boss'].includes(userStore.role))

async function fetchCompanies() {
  loading.value = true
  try {
    companies.value = await getLogisticsCompanies()
  } catch (error) {
    ElMessage.error('获取物流公司列表失败')
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  dialogMode.value = 'create'
  dialogVisible.value = true
}

function editCompany(row) {
  currentCompany.value = row
  dialogMode.value = 'edit'
  companyForm.company_code = row.company_code
  companyForm.company_name = row.company_name
  companyForm.contact_person = row.contact_person
  companyForm.contact_phone = row.contact_phone
  companyForm.status = row.status
  dialogVisible.value = true
}

async function deleteCompany(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除物流公司 ${row.company_name} 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteCompanyApi(row.id)
    ElMessage.success('删除成功')
    fetchCompanies()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function submitCompany() {
  if (!companyFormRef.value) return

  try {
    await companyFormRef.value.validate()
    submitting.value = true
    try {
      const data = {
        company_code: companyForm.company_code,
        company_name: companyForm.company_name,
        contact_person: companyForm.contact_person,
        contact_phone: companyForm.contact_phone,
        status: companyForm.status
      }

      if (dialogMode.value === 'create') {
        await createLogisticsCompany(data)
        ElMessage.success('创建成功')
      } else {
        await updateLogisticsCompany(currentCompany.value.id, data)
        ElMessage.success('更新成功')
      }

      dialogVisible.value = false
      fetchCompanies()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  } catch {
    // 表单验证未通过
  }
}

function resetForm() {
  companyFormRef.value?.resetFields()
  companyForm.company_code = ''
  companyForm.company_name = ''
  companyForm.contact_person = ''
  companyForm.contact_phone = ''
  companyForm.status = 'active'
  currentCompany.value = null
}

onMounted(() => {
  fetchCompanies()
})
</script>

<style scoped>
.logistics-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
