<template>
  <div class="platform-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>基础信息 - 平台管理</span>
          <el-button type="primary" @click="showCreateDialog">新增平台</el-button>
        </div>
      </template>

      <el-table :data="platforms" v-loading="loading" border style="width: 100%" empty-text="暂无平台">
        <el-table-column prop="platform_code" label="编码" width="90" align="center" />
        <el-table-column prop="platform_name" label="平台名称" min-width="160" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑 对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="680px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="平台编码" prop="platform_code">
          <el-input v-model="form.platform_code" maxlength="50" show-word-limit
                    placeholder="如 aliexpress / alibaba_icbu（唯一，不可重复）" />
        </el-form-item>
        <el-form-item label="平台名称" prop="platform_name">
          <el-input v-model="form.platform_name" maxlength="100" show-word-limit placeholder="请输入平台名称" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="255"
                    placeholder="可填写平台说明（对接前占位）" />
        </el-form-item>

        <el-divider content-position="left">API 对接配置（预留字段，对接各平台时填写）</el-divider>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="API 网关地址">
              <el-input v-model="form.api_gateway" placeholder="如 https://gw.open.1688.com" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="接口版本">
              <el-input v-model="form.api_version" placeholder="如 v3 / top2.0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="总 QPS 上限">
              <el-input-number v-model="form.api_global_max_qps" :min="1" :max="9999" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12"></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="TOP 签名算法">
              <el-input v-model="form.top_sign_type" placeholder="如 hmac-sha1" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Webhook 加密">
              <el-input v-model="form.webhook_encrypt_type" placeholder="如 sha256" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="TOP 默认字段">
          <el-input v-model="form.top_default_fields" placeholder="订单默认查询字段，逗号分隔" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="REST 鉴权 Header">
              <el-input v-model="form.rest_auth_header" placeholder="如 Authorization" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Token 前缀">
              <el-input v-model="form.rest_token_prefix" placeholder="如 Bearer" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'PlatformManagement' })
import { ref, reactive, computed, onMounted } from 'vue'
import { platformApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const platforms = ref([])

const dialogVisible = ref(false)
const dialogMode = ref('create')
const dialogTitle = computed(() => dialogMode.value === 'create' ? '新增平台' : '编辑平台')

const formRef = ref(null)
const emptyForm = () => ({
  platform_code: '',
  platform_name: '',
  status: 1,
  remark: '',
  api_gateway: '',
  api_version: '',
  api_global_max_qps: 10,
  top_sign_type: '',
  top_default_fields: '',
  rest_auth_header: '',
  rest_token_prefix: '',
  webhook_encrypt_type: ''
})
const form = reactive(emptyForm())

const rules = {
  platform_code: [{ required: true, message: '请输入平台编码', trigger: 'blur' }],
  platform_name: [{ required: true, message: '请输入平台名称', trigger: 'blur' }]
}

async function fetchPlatforms() {
  loading.value = true
  try {
    platforms.value = (await platformApi.getPlatforms()) || []
  } catch (e) {
    ElMessage.error('加载平台失败')
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
}

function showEditDialog(row) {
  dialogMode.value = 'edit'
  Object.assign(form, emptyForm(), row)
  dialogVisible.value = true
}

function resetForm() {
  Object.assign(form, emptyForm())
  formRef.value?.clearValidate()
}

async function submit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload = {
      platform_code: form.platform_code.trim(),
      platform_name: form.platform_name.trim(),
      status: form.status,
      remark: form.remark,
      api_gateway: form.api_gateway || null,
      api_version: form.api_version || null,
      api_global_max_qps: form.api_global_max_qps,
      top_sign_type: form.top_sign_type || null,
      top_default_fields: form.top_default_fields || null,
      rest_auth_header: form.rest_auth_header || null,
      rest_token_prefix: form.rest_token_prefix || null,
      webhook_encrypt_type: form.webhook_encrypt_type || null
    }
    if (dialogMode.value === 'create') {
      await platformApi.createPlatform(payload)
      ElMessage.success('平台创建成功')
    } else {
      await platformApi.updatePlatform(form.platform_code, payload)
      ElMessage.success('平台更新成功')
    }
    dialogVisible.value = false
    await fetchPlatforms()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除平台 [${row.platform_code}] ${row.platform_name} 吗？`,
      '确认删除',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await platformApi.deletePlatform(row.platform_code)
    ElMessage.success('平台已删除')
    await fetchPlatforms()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      // 已关联网店时后端返回 400，detail 已含原因
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(fetchPlatforms)
</script>

<style scoped>
.platform-page { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.readonly-code { color: #606266; font-size: 13px; }
</style>
