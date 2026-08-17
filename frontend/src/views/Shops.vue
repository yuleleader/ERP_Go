<template>
  <div class="shops-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>基础信息 - 网店管理</span>
          <el-button v-if="canAdd" type="primary" @click="showShopCreateDialog">新建网店</el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="网店名称">
          <el-input v-model="shopFilters.shopName" placeholder="请输入网店名称" clearable @change="fetchShops" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="shopFilters.status" placeholder="请选择" clearable @change="fetchShops">
            <el-option label="正常" value="normal" />
            <el-option label="关店" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchShops">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="shops" v-loading="shopLoading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="shop_id" label="网店ID" width="180" />
        <el-table-column prop="shop_name" label="网店名称" />
        <el-table-column label="所属平台" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.platform_name" type="primary" effect="plain">{{ row.platform_name }}</el-tag>
            <span v-else style="color: #909399">未关联（手工）</span>
          </template>
        </el-table-column>
        <el-table-column prop="shop_account" label="网店账号" />
        <el-table-column prop="creator" label="创建者" width="110" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'normal' ? 'success' : 'info'">
              {{ row.status === 'normal' ? '正常' : '关店' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="order_count" label="关联订单" width="100" />
        <el-table-column prop="create_time" label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canEdit" link type="primary" size="small" @click="editShop(row)">编辑</el-button>
            <el-button link type="info" size="small" @click="showDetail(row)">查看详情</el-button>
            <el-button v-if="row.platform_id" link type="success" size="small"
                       :loading="syncLoadingId === row.shop_id" @click="handleSync(row)">立即同步订单</el-button>
            <el-button v-if="canDelete" link type="danger" size="small" @click="handleDeleteShop(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建 / 编辑 网店弹窗 -->
    <el-dialog v-model="shopDialogVisible" :title="shopDialogTitle" width="720px" @closed="resetShopForm">
      <el-form ref="shopFormRef" :model="shopForm" :rules="shopRules" label-width="120px">
        <el-divider content-position="left">基础信息</el-divider>
        <el-form-item label="网店名称" prop="shop_name">
          <el-input v-model="shopForm.shop_name" placeholder="请输入网店名称" />
        </el-form-item>
        <el-form-item label="网店账号" prop="shop_account">
          <el-input v-model="shopForm.shop_account" placeholder="请输入网店账号" :disabled="shopDialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="所属平台" prop="platform_id">
          <el-select v-model="shopForm.platform_id" placeholder="请选择平台（可留空=手工录入）" style="width: 100%"
                     @change="onPlatformChange">
            <el-option label="无（手工录入网店）" :value="''" />
            <el-option v-for="p in allPlatforms" :key="p.id" :label="p.platform_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="shopForm.status">
            <el-radio label="normal">正常</el-radio>
            <el-radio label="closed">关店</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 平台公共配置只读预览（选择具体平台且 platform_id 不为 null 时显示） -->
        <el-alert
          v-if="selectedPlatform"
          type="info" :closable="false" show-icon
          :title="`平台公共配置（在【平台管理】菜单维护，此处只读）`"
          style="margin-bottom: 12px">
          <template #default>
            <div class="plat-preview">
              <span>网关：{{ selectedPlatform.api_gateway || '—' }}</span>
              <span>版本：{{ selectedPlatform.api_version || '—' }}</span>
              <span>签名：{{ selectedPlatform.top_sign_type || '—' }}</span>
              <span>鉴权Header：{{ selectedPlatform.rest_auth_header || '—' }}</span>
            </div>
          </template>
        </el-alert>

        <!-- 店铺级 API 配置面板：仅老板可见可编辑；销售打开整组隐藏 -->
        <template v-if="isBoss && shopForm.platform_id">
          <el-collapse v-model="apiConfigCollapse" style="border: none; margin-top: 4px">
            <el-collapse-item name="api" style="border-top: 1px solid var(--el-border-color-lighter)">
              <template #title>
                <span style="font-weight: 600">店铺 API 配置（仅老板可见/可编辑）</span>
              </template>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="App Key">
                    <el-input v-model="shopForm.api_app_key" placeholder="店铺私有 AppKey" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="App Secret">
                    <el-input v-model="shopForm.api_app_secret" type="password" show-password placeholder="店铺私有密钥（加密存储）" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="Access Token">
                <el-input v-model="shopForm.api_access_token" type="textarea" :rows="2" placeholder="OAuth 访问令牌（加密存储）" />
              </el-form-item>
              <el-form-item label="Refresh Token">
                <el-input v-model="shopForm.api_refresh_token" type="textarea" :rows="2" placeholder="OAuth 刷新令牌（加密存储）" />
              </el-form-item>
              <el-row :gutter="16">
                <el-col :span="8">
                  <el-form-item label="单店QPS">
                    <el-input-number v-model="shopForm.api_self_qps" :min="1" :max="9999" controls-position="right" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="自动同步">
                    <el-switch v-model="shopForm.sync_auto_enable" :active-value="1" :inactive-value="0" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="同步间隔(分)">
                    <el-input-number v-model="shopForm.sync_order_interval" :min="1" :max="1440" controls-position="right" style="width:100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="8">
                  <el-form-item label="拉取窗口(时)">
                    <el-input-number v-model="shopForm.sync_time_window" :min="1" :max="72" controls-position="right" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="重试次数">
                    <el-input-number v-model="shopForm.api_retry_count" :min="0" :max="10" controls-position="right" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="重试间隔(ms)">
                    <el-input-number v-model="shopForm.api_retry_base_ms" :min="100" :max="60000" :step="100" controls-position="right" style="width:100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="Webhook 回调">
                    <el-input v-model="shopForm.webhook_callback" placeholder="店铺独立 webhook 地址" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Webhook 验签密钥">
                    <el-input v-model="shopForm.webhook_verify_key" placeholder="webhook 验签密钥（加密存储）" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="扩展 JSON">
                <el-input v-model="shopForm.api_ext_json" type="textarea" :rows="2" placeholder="店铺特殊参数（高级配置）" />
              </el-form-item>
            </el-collapse-item>
          </el-collapse>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="shopDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitShop" :loading="shopSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情弹窗（只读） -->
    <el-dialog v-model="detailVisible" title="网店详情" width="720px">
      <el-descriptions :column="2" border size="small" v-if="detailRow">
        <el-descriptions-item label="网店ID">{{ detailRow.shop_id }}</el-descriptions-item>
        <el-descriptions-item label="网店名称">{{ detailRow.shop_name }}</el-descriptions-item>
        <el-descriptions-item label="所属平台">
          {{ detailRow.platform_name || '未关联（手工录入）' }}
        </el-descriptions-item>
        <el-descriptions-item label="网店账号">{{ detailRow.shop_account }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ detailRow.status === 'normal' ? '正常' : '关店' }}</el-descriptions-item>
        <el-descriptions-item label="创建者">{{ detailRow.creator }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(detailRow.create_time) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(detailRow.update_time) }}</el-descriptions-item>

        <template v-if="isBoss && detailRow.platform_id">
          <el-descriptions-item label="App Key">{{ detailRow.api_app_key || '—' }}</el-descriptions-item>
          <el-descriptions-item label="App Secret">{{ maskSecret(detailRow.api_app_secret) }}</el-descriptions-item>
          <el-descriptions-item label="Access Token" :span="2">{{ maskSecret(detailRow.api_access_token) }}</el-descriptions-item>
          <el-descriptions-item label="单店QPS">{{ detailRow.api_self_qps ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="自动同步">{{ detailRow.sync_auto_enable === 1 ? '开启' : '关闭' }}</el-descriptions-item>
          <el-descriptions-item label="同步间隔(分)">{{ detailRow.sync_order_interval ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="拉取窗口(时)">{{ detailRow.sync_time_window ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="重试次数">{{ detailRow.api_retry_count ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="重试间隔(ms)">{{ detailRow.api_retry_base_ms ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="上次成功同步" :span="2">{{ formatDateTime(detailRow.last_sync_success_time) || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Token 过期时间">{{ formatDateTime(detailRow.api_token_expire) || '—' }}</el-descriptions-item>
          <el-descriptions-item label="授权范围">{{ detailRow.api_auth_scope || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Webhook 回调" :span="2">{{ detailRow.webhook_callback || '—' }}</el-descriptions-item>
        </template>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'Shops' })
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { checkDataPerm } from '@/utils/dataPerm'
import { getShops, createShop, updateShop, deleteShop, syncShopOrders } from '@/api/shop'
import { platformApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'

const userStore = useUserStore()
const isBoss = computed(() => userStore.userInfo?.role === 'boss')
const canAdd = computed(() => checkDataPerm(userStore.userInfo, '/shops', 'add'))
const canEdit = computed(() => checkDataPerm(userStore.userInfo, '/shops', 'edit'))
const canDelete = computed(() => checkDataPerm(userStore.userInfo, '/shops', 'delete'))

const shopLoading = ref(false)
const shops = ref([])
const shopDialogVisible = ref(false)
const shopDialogMode = ref('create')
const shopSubmitting = ref(false)
const shopFormRef = ref(null)
const apiConfigCollapse = ref([]) // 店铺 API 配置折叠面板，默认空=收起

const shopForm = reactive({
  shop_id: '',
  shop_name: '',
  shop_account: '',
  platform_id: '',
  status: 'normal',
  // 店铺级 API 配置（仅 boss 使用）
  api_app_key: '',
  api_app_secret: '',
  api_access_token: '',
  api_refresh_token: '',
  api_self_qps: 8,
  sync_auto_enable: 1,
  sync_order_interval: 5,
  sync_time_window: 1,
  api_retry_count: 3,
  api_retry_base_ms: 1000,
  webhook_callback: '',
  webhook_verify_key: '',
  api_ext_json: ''
})

const shopRules = {
  shop_name: [{ required: true, message: '请输入网店名称', trigger: 'blur' }],
  shop_account: [{ required: true, message: '请输入网店账号', trigger: 'blur' }]
}

const platforms = ref([])
const allPlatforms = computed(() => platforms.value)
const selectedPlatform = computed(() =>
  shopForm.platform_id ? platforms.value.find(p => p.id === shopForm.platform_id) : null
)
async function fetchPlatforms() {
  try {
    platforms.value = await platformApi.getPlatforms()
  } catch (e) {
    platforms.value = []
  }
}

const shopFilters = reactive({ shopName: '', status: '' })
const shopDialogTitle = computed(() => shopDialogMode.value === 'create' ? '新建网店' : '编辑网店')

async function fetchShops() {
  shopLoading.value = true
  try {
    const params = {}
    if (shopFilters.shopName) params.shop_name = shopFilters.shopName
    if (shopFilters.status) params.status = shopFilters.status
    shops.value = await getShops(params)
  } catch (error) {
    ElMessage.error('获取网店列表失败')
  } finally {
    shopLoading.value = false
  }
}

function onPlatformChange() {
  // 选择具体平台时，自动把「网店名称」填充为平台名称
  if (shopForm.platform_id) {
    const p = allPlatforms.value.find(x => x.id === shopForm.platform_id)
    if (p) {
      shopForm.shop_name = p.platform_name
    }
  }
  // 切到「无」时模板中 API 面板会自动隐藏
}

function showShopCreateDialog() {
  shopDialogMode.value = 'create'
  resetShopForm()
  shopDialogVisible.value = true
}

function editShop(row) {
  shopDialogMode.value = 'edit'
  shopForm.shop_id = row.shop_id
  shopForm.shop_name = row.shop_name
  shopForm.shop_account = row.shop_account
  shopForm.platform_id = row.platform_id || ''
  shopForm.status = row.status
  // 仅 boss 回填 API 配置（销售响应中这些字段为 null，且面板隐藏）
  if (isBoss.value) {
    shopForm.api_app_key = row.api_app_key || ''
    shopForm.api_app_secret = row.api_app_secret || ''
    shopForm.api_access_token = row.api_access_token || ''
    shopForm.api_refresh_token = row.api_refresh_token || ''
    shopForm.api_self_qps = row.api_self_qps ?? 8
    shopForm.sync_auto_enable = row.sync_auto_enable ?? 1
    shopForm.sync_order_interval = row.sync_order_interval ?? 5
    shopForm.sync_time_window = row.sync_time_window ?? 1
    shopForm.api_retry_count = row.api_retry_count ?? 3
    shopForm.api_retry_base_ms = row.api_retry_base_ms ?? 1000
    shopForm.webhook_callback = row.webhook_callback || ''
    shopForm.webhook_verify_key = row.webhook_verify_key || ''
    shopForm.api_ext_json = row.api_ext_json || ''
  }
  shopDialogVisible.value = true
}

function buildPayload() {
  const payload = {
    shop_name: shopForm.shop_name,
    shop_account: shopForm.shop_account,
    status: shopForm.status,
    platform_id: shopForm.platform_id === '' ? null : shopForm.platform_id
  }
  // 店铺级 API 配置仅老板提交（销售不触碰，避免误清空密钥）
  if (isBoss.value) {
    payload.api_app_key = shopForm.api_app_key || null
    payload.api_app_secret = shopForm.api_app_secret || null
    payload.api_access_token = shopForm.api_access_token || null
    payload.api_refresh_token = shopForm.api_refresh_token || null
    payload.api_self_qps = shopForm.api_self_qps
    payload.sync_auto_enable = shopForm.sync_auto_enable
    payload.sync_order_interval = shopForm.sync_order_interval
    payload.sync_time_window = shopForm.sync_time_window
    payload.api_retry_count = shopForm.api_retry_count
    payload.api_retry_base_ms = shopForm.api_retry_base_ms
    payload.webhook_callback = shopForm.webhook_callback || null
    payload.webhook_verify_key = shopForm.webhook_verify_key || null
    payload.api_ext_json = shopForm.api_ext_json || null
  }
  return payload
}

async function submitShop() {
  if (!shopFormRef.value) return
  try {
    await shopFormRef.value.validate()
    shopSubmitting.value = true
    try {
      const payload = buildPayload()
      if (shopDialogMode.value === 'create') {
        await createShop(payload)
        ElMessage.success('网店创建成功')
      } else {
        await updateShop(shopForm.shop_id, payload)
        ElMessage.success('网店更新成功')
      }
      shopDialogVisible.value = false
      fetchShops()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      shopSubmitting.value = false
    }
  } catch {
    // 表单验证未通过
  }
}

function resetShopForm() {
  shopFormRef.value?.resetFields()
  Object.assign(shopForm, {
    shop_id: '', shop_name: '', shop_account: '', platform_id: '', status: 'normal',
    api_app_key: '', api_app_secret: '', api_access_token: '', api_refresh_token: '',
    api_self_qps: 8, sync_auto_enable: 1, sync_order_interval: 5, sync_time_window: 1,
    api_retry_count: 3, api_retry_base_ms: 1000, webhook_callback: '', webhook_verify_key: '', api_ext_json: ''
  })
}

async function handleDeleteShop(row) {
  try {
    await ElMessageBox.confirm(`确定要删除网店 ${row.shop_name} 吗？`, '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
    })
    await deleteShop(row.shop_id)
    ElMessage.success('网店删除成功')
    fetchShops()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// ==================== 详情 + 同步 ====================
const detailVisible = ref(false)
const detailRow = ref(null)
function showDetail(row) {
  detailRow.value = row
  detailVisible.value = true
}

function maskSecret(v) {
  if (!v) return '—'
  if (v.length <= 6) return v
  return v.slice(0, 4) + '****' + v.slice(-2)
}

const syncLoadingId = ref('')
async function handleSync(row) {
  syncLoadingId.value = row.shop_id
  try {
    const res = await syncShopOrders(row.shop_id)
    ElMessage.success((res && res.message) ? res.message : '同步完成')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '同步失败')
  } finally {
    syncLoadingId.value = ''
    fetchShops()
  }
}

onMounted(() => { fetchShops(); fetchPlatforms() })
</script>

<style scoped>
.shops-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-form { margin-bottom: 20px; margin-top: 10px; }
.filter-form .el-select { width: 150px; }
.plat-preview { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 12px; color: #606266; }
</style>
