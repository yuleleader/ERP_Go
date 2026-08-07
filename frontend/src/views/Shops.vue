<template>
  <div class="shops-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>基础信息 - 网店管理</span>
          <el-button type="primary" @click="showShopCreateDialog">新建网店</el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="平台">
          <el-input v-model="shopFilters.shopName" placeholder="请输入平台" clearable @change="fetchShops" />
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
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="shop_id" label="网店ID" width="200" />
        <el-table-column prop="shop_name" label="平台" />
        <el-table-column prop="shop_account" label="网店账号" />
        <el-table-column prop="creator" label="创建者" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'normal' ? 'success' : 'info'">
              {{ row.status === 'normal' ? '正常' : '关店' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="order_count" label="关联订单数" width="120" />
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editShop(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDeleteShop(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 网店管理弹窗 -->
    <el-dialog v-model="shopDialogVisible" :title="shopDialogTitle" width="500px" @closed="resetShopForm">
      <el-form ref="shopFormRef" :model="shopForm" :rules="shopRules" label-width="100px">
        <el-form-item label="平台" prop="shop_name">
          <el-input v-model="shopForm.shop_name" placeholder="请输入平台" />
        </el-form-item>
        <el-form-item label="网店账号" prop="shop_account">
          <el-input v-model="shopForm.shop_account" placeholder="请输入网店账号" :disabled="shopDialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="shopForm.status">
            <el-radio label="normal">正常</el-radio>
            <el-radio label="closed">关店</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="shopDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitShop" :loading="shopSubmitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { getShops, createShop, updateShop, deleteShop } from '@/api/shop'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'

const shopLoading = ref(false)
const shops = ref([])
const shopDialogVisible = ref(false)
const shopDialogMode = ref('create')
const shopSubmitting = ref(false)
const shopFormRef = ref(null)

const shopForm = reactive({
  shop_id: '',
  shop_name: '',
  shop_account: '',
  status: 'normal'
})

const shopRules = {
  shop_name: [{ required: true, message: '请输入平台', trigger: 'blur' }],
  shop_account: [{ required: true, message: '请输入网店账号', trigger: 'blur' }]
}

const shopFilters = reactive({
  shopName: '',
  status: ''
})

const shopDialogTitle = computed(() => 
  shopDialogMode.value === 'create' ? '新建网店' : '编辑网店'
)

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

function showShopCreateDialog() {
  shopDialogMode.value = 'create'
  shopDialogVisible.value = true
}

function editShop(row) {
  shopDialogMode.value = 'edit'
  shopForm.shop_id = row.shop_id
  shopForm.shop_name = row.shop_name
  shopForm.shop_account = row.shop_account
  shopForm.status = row.status
  shopDialogVisible.value = true
}

async function submitShop() {
  if (!shopFormRef.value) return
  try {
    await shopFormRef.value.validate()
    shopSubmitting.value = true
    try {
      if (shopDialogMode.value === 'create') {
        await createShop(shopForm)
        ElMessage.success('网店创建成功')
      } else {
        const { shop_id, ...shopPayload } = shopForm
        await updateShop(shop_id, shopPayload)
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
  shopForm.shop_name = ''
  shopForm.shop_account = ''
  shopForm.status = 'normal'
}

async function handleDeleteShop(row) {
  try {
    await ElMessageBox.confirm(`确定要删除网店 ${row.shop_name} 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
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

fetchShops()
</script>

<style scoped>
.shops-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 20px;
  margin-top: 10px;
}

.filter-form .el-select {
  width: 150px;
}
</style>