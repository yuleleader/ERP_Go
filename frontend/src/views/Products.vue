<template>
  <div class="products-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>商品管理</span>
          <el-button type="primary" @click="showCreateDialog">新建商品</el-button>
        </div>
      </template>

      <!-- 搜索筛选区域 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="关键词">
          <el-input 
            v-model="filters.keyword" 
            placeholder="商品编码/商品名称" 
            clearable 
            @change="fetchProducts"
            style="width: 200px;"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select 
            v-model="filters.status" 
            placeholder="请选择" 
            clearable 
            @change="fetchProducts"
            style="width: 120px;"
          >
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchProducts">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 批量操作区域 -->
      <div class="batch-actions" v-if="selectedProducts.length > 0">
        <el-button type="danger" @click="handleBatchDelete">
          批量删除 ({{ selectedProducts.length }})
        </el-button>
      </div>

      <!-- 商品列表表格 -->
      <el-table 
        :data="products" 
        v-loading="loading" 
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="product_code" label="商品编码" width="150" />
        <el-table-column prop="product_name" label="商品名称" min-width="200" />
        <el-table-column prop="product_remark" label="备注" min-width="200">
          <template #default="{ row }">
            <div v-if="row.product_remark" class="remark-cell">
              {{ row.product_remark }}
            </div>
            <span v-else style="color: #999;">暂无备注</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewProduct(row)">查看</el-button>
            <el-button link type="primary" size="small" @click="editProduct(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDeleteProduct(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.limit"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchProducts"
        @current-change="fetchProducts"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>

    <!-- 创建/编辑商品对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogTitle" 
      width="600px" 
      @closed="resetForm"
    >
      <el-form 
        ref="productFormRef" 
        :model="productForm" 
        :rules="productRules" 
        label-width="100px"
      >
        <el-form-item label="商品编码" v-if="dialogMode === 'edit'">
          <el-input v-model="productForm.product_code" disabled />
        </el-form-item>
        <el-form-item label="商品名称" prop="product_name">
          <el-input 
            v-model="productForm.product_name" 
            placeholder="请输入商品名称（2-100字符）"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="商品备注" prop="product_remark">
          <el-input 
            v-model="productForm.product_remark" 
            type="textarea" 
            :rows="4"
            placeholder="请输入商品备注（最多500字符）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="商品状态" v-if="dialogMode === 'edit'">
          <el-select v-model="productForm.status" placeholder="请选择状态">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitProduct" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 商品详情对话框 -->
    <el-dialog 
      v-model="viewDialogVisible" 
      title="商品详情" 
      width="600px"
    >
      <div class="product-detail">
        <div class="detail-item">
          <span class="label">商品编码：</span>
          <span class="value">{{ currentProduct.product_code }}</span>
        </div>
        <div class="detail-item">
          <span class="label">商品名称：</span>
          <span class="value">{{ currentProduct.product_name }}</span>
        </div>
        <div class="detail-item">
          <span class="label">商品状态：</span>
          <el-tag :type="currentProduct.status === 'active' ? 'success' : 'info'">
            {{ currentProduct.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </div>
        <div class="detail-item">
          <span class="label">商品备注：</span>
          <div class="remark-content">
            {{ currentProduct.product_remark || '暂无备注' }}
          </div>
        </div>
        <div class="detail-item">
          <span class="label">创建人：</span>
          <span class="value">{{ currentProduct.created_by }}</span>
        </div>
        <div class="detail-item">
          <span class="label">创建时间：</span>
          <span class="value">{{ formatDateTime(currentProduct.created_at) }}</span>
        </div>
        <div class="detail-item">
          <span class="label">更新时间：</span>
          <span class="value">{{ formatDateTime(currentProduct.updated_at) }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 商品管理页面组件
 * 实现商品档案的全生命周期维护功能
 * 权限控制：仅老板端角色可访问
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { 
  getProducts, 
  getProductDetail, 
  createProduct, 
  updateProduct, 
  deleteProduct,
  batchDeleteProducts,
  getProductCount
} from '@/api/product'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'

// 用户状态管理
const userStore = useUserStore()

// 权限检查：老板端和销售端可以访问商品管理
const canManageProducts = computed(() => ['boss', 'sales'].includes(userStore.userInfo?.role))

// 数据状态
const loading = ref(false)
const products = ref([])
const selectedProducts = ref([])

// 分页配置
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 搜索筛选
const filters = reactive({
  keyword: '',
  status: ''
})

// 对话框状态
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)

// 表单引用
const productFormRef = ref(null)

// 商品表单数据
const productForm = reactive({
  product_code: '',
  product_name: '',
  product_remark: '',
  status: 'active'
})

// 当前查看的商品
const currentProduct = ref({})

// 表单验证规则
const productRules = {
  product_name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' },
    { min: 2, max: 100, message: '商品名称长度应在2-100字符之间', trigger: 'blur' }
  ],
  product_remark: [
    { max: 500, message: '商品备注不能超过500字符', trigger: 'blur' }
  ]
}

// 对话框标题
const dialogTitle = computed(() => 
  dialogMode.value === 'create' ? '新建商品' : '编辑商品'
)

/**
 * 获取商品列表
 */
async function fetchProducts() {
  // 权限检查
  if (!canManageProducts.value) {
    ElMessage.warning('您没有权限访问商品管理')
    return
  }

  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit,
      keyword: filters.keyword || undefined,
      status: filters.status || undefined
    }
    
    const response = await getProducts(params)
    products.value = response
    
    // 获取总数：无筛选条件时用全量count，有筛选时用返回列表长度估算
    if (!filters.keyword && !filters.status) {
      const countResponse = await getProductCount()
      pagination.total = countResponse.total
    } else {
      pagination.total = (products.value && products.value.length) || 0
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取商品列表失败')
  } finally {
    loading.value = false
  }
}

/**
 * 重置筛选条件
 */
function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  pagination.page = 1
  fetchProducts()
}

/**
 * 显示创建商品对话框
 */
function showCreateDialog() {
  dialogMode.value = 'create'
  dialogVisible.value = true
}

/**
 * 查看商品详情
 */
async function viewProduct(row) {
  try {
    const response = await getProductDetail(row.product_code)
    currentProduct.value = response
    viewDialogVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取商品详情失败')
  }
}

/**
 * 编辑商品
 */
function editProduct(row) {
  dialogMode.value = 'edit'
  productForm.product_code = row.product_code
  productForm.product_name = row.product_name
  productForm.product_remark = row.product_remark || ''
  productForm.status = row.status
  dialogVisible.value = true
}

/**
 * 提交商品表单
 */
async function submitProduct() {
  if (!productFormRef.value) return

  try {
    await productFormRef.value.validate()
    submitting.value = true
    try {
      const data = {
        product_name: productForm.product_name,
        product_remark: productForm.product_remark
      }

      if (dialogMode.value === 'create') {
        await createProduct(data)
        ElMessage.success('商品创建成功')
      } else {
        data.status = productForm.status
        await updateProduct(productForm.product_code, data)
        ElMessage.success('商品更新成功')
      }

      dialogVisible.value = false
      fetchProducts()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  } catch {
    // 表单验证未通过
  }
}

/**
 * 重置表单
 */
function resetForm() {
  productFormRef.value?.resetFields()
  productForm.product_code = ''
  productForm.product_name = ''
  productForm.product_remark = ''
  productForm.status = 'active'
}

/**
 * 删除单个商品
 */
async function handleDeleteProduct(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除商品 "${row.product_name}" 吗？删除后无法恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteProduct(row.product_code)
    ElMessage.success('商品删除成功')
    fetchProducts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

/**
 * 处理表格选择变化
 */
function handleSelectionChange(selection) {
  selectedProducts.value = selection
}

/**
 * 批量删除商品
 */
async function handleBatchDelete() {
  if (selectedProducts.value.length === 0) {
    ElMessage.warning('请选择要删除的商品')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedProducts.value.length} 个商品吗？删除后无法恢复。`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const productCodes = selectedProducts.value.map(p => p.product_code)
    await batchDeleteProducts(productCodes)
    ElMessage.success('批量删除成功')
    selectedProducts.value = []
    fetchProducts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '批量删除失败')
    }
  }
}

// 页面加载时获取商品列表
onMounted(() => {
  if (canManageProducts.value) {
    fetchProducts()
  } else {
    ElMessage.warning('您没有权限访问商品管理模块')
  }
})
</script>

<style scoped>
.products-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 20px;
}

.batch-actions {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.remark-cell {
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-detail {
  padding: 20px;
}

.detail-item {
  display: flex;
  margin-bottom: 20px;
  align-items: flex-start;
}

.detail-item .label {
  width: 100px;
  color: #666;
  font-weight: 500;
  flex-shrink: 0;
}

.detail-item .value {
  color: #333;
  flex: 1;
}

.remark-content {
  flex: 1;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
}
</style>