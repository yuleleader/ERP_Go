<template>
  <div class="products-container">
    <div class="products-layout">
      <!-- 左侧：类别 / 品牌 导航 -->
      <div class="left-panel">
        <div class="left-header">
          <el-radio-group v-model="leftMode" size="small">
            <el-radio-button label="category">类别</el-radio-button>
            <el-radio-button label="brand">品牌</el-radio-button>
          </el-radio-group>
        </div>
        <div class="left-list" v-loading="leftLoading">
          <div
            class="left-item"
            :class="{ active: !selectedId }"
            @click="selectLeft(null)"
          >
            全部
          </div>
          <template v-if="leftMode === 'category'">
            <div
              v-for="cat in categoryFlat"
              :key="cat.id"
              class="left-item"
              :class="{ active: selectedId === cat.id, indent: cat.level > 1 }"
              @click="selectLeft(cat.id)"
            >
              <span class="item-name">{{ cat.category_name }}</span>
              <span class="item-code">{{ cat.category_code }}</span>
            </div>
          </template>
          <template v-else>
            <div
              v-for="b in brands"
              :key="b.id"
              class="left-item"
              :class="{ active: selectedId === b.id }"
              @click="selectLeft(b.id)"
            >
              <span class="item-name">{{ b.brand_name }}</span>
              <span class="item-code">{{ b.brand_code }}</span>
            </div>
          </template>
          <div v-if="!leftLoading && currentLeftList.length === 0" class="left-empty">
            暂无{{ leftMode === 'category' ? '类别' : '品牌' }}，请先在基础信息中维护
          </div>
        </div>
      </div>

      <!-- 右侧：商品列表 -->
      <div class="right-panel">
        <div class="right-toolbar">
          <el-input
            v-model="filters.keyword"
            placeholder="商品编码 / 商品名称"
            clearable
            style="width: 220px;"
            @change="fetchProducts"
          />
          <el-select
            v-model="filters.status"
            placeholder="状态"
            clearable
            style="width: 120px;"
            @change="fetchProducts"
          >
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
          <el-button type="primary" @click="fetchProducts">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <div class="toolbar-spacer"></div>
          <el-button type="primary" @click="showCreateDialog">新建商品</el-button>
        </div>

        <div class="batch-actions" v-if="selectedProducts.length > 0">
          <el-button type="danger" size="small" @click="handleBatchDelete">
            批量删除 ({{ selectedProducts.length }})
          </el-button>
        </div>

        <el-table
          :data="products"
          v-loading="loading"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="product_code" label="商品编码" width="130" />
          <el-table-column prop="product_name" label="商品名称" min-width="160" />
          <el-table-column label="类别" width="140">
            <template #default="{ row }">
              {{ categoryName(row.category_id) }}
            </template>
          </el-table-column>
          <el-table-column label="品牌" width="120">
            <template #default="{ row }">
              {{ brandName(row.brand_id) }}
            </template>
          </el-table-column>
          <el-table-column prop="product_remark" label="备注" min-width="160" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'">
                {{ row.status === 'active' ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="170" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="viewProduct(row)">查看</el-button>
              <el-button link type="primary" size="small" @click="editProduct(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDeleteProduct(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchProducts"
          @current-change="fetchProducts"
          style="margin-top: 15px; justify-content: flex-end;"
        />
      </div>
    </div>

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
        <el-form-item label="所属类别">
          <el-select v-model="productForm.category_id" placeholder="请选择类别" clearable style="width: 100%;" filterable>
            <el-option
              v-for="cat in categoryFlat"
              :key="cat.id"
              :label="catLevelLabel(cat)"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="所属品牌">
          <el-select v-model="productForm.brand_id" placeholder="请选择品牌" clearable style="width: 100%;" filterable>
            <el-option
              v-for="b in brands"
              :key="b.id"
              :label="`${b.brand_name}（${b.brand_code}）`"
              :value="b.id"
            />
          </el-select>
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
    <el-dialog v-model="viewDialogVisible" title="商品详情" width="600px">
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
          <span class="label">所属类别：</span>
          <span class="value">{{ categoryName(currentProduct.category_id) || '未设置' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">所属品牌：</span>
          <span class="value">{{ brandName(currentProduct.brand_id) || '未设置' }}</span>
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
 * 商品管理页面（主从布局）
 * 左侧：类别 / 品牌（上方切换按钮），右侧：对应商品列表 + 搜索 + 新增
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
import { getCategories } from '@/api/category'
import { getBrands } from '@/api/brand'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'

const userStore = useUserStore()

// 权限检查：老板端和销售端可以访问商品管理
const canManageProducts = computed(() => ['boss', 'sales'].includes(userStore.userInfo?.role))

// ===== 左侧导航 =====
const leftMode = ref('category')        // category | brand
const selectedId = ref(null)            // 选中的类别/品牌 id（null=全部）
const leftLoading = ref(false)
const categories = ref([])              // 树形结构
const brands = ref([])

// 拉平类别（含二级），用于左侧列表与下拉
const categoryFlat = computed(() => {
  const list = []
  const walk = (nodes) => {
    for (const n of nodes || []) {
      list.push(n)
      if (n.children && n.children.length) walk(n.children)
    }
  }
  walk(categories.value)
  return list
})

const currentLeftList = computed(() => (leftMode.value === 'category' ? categoryFlat.value : brands.value))

// 编码/名称映射
const categoryMap = computed(() => {
  const m = {}
  for (const c of categoryFlat.value) m[c.id] = c
  return m
})
const brandMap = computed(() => {
  const m = {}
  for (const b of brands.value) m[b.id] = b
  return m
})
const categoryName = (id) => (id ? categoryMap.value[id]?.category_name || '' : '')
const brandName = (id) => (id ? brandMap.value[id]?.brand_name || '' : '')
const catLevelLabel = (cat) =>
  cat.level > 1 ? `　　${cat.category_name}（${cat.category_code}）` : `${cat.category_name}（${cat.category_code}）`

// 加载左侧数据
async function loadLeftData() {
  leftLoading.value = true
  try {
    const [catRes, brandRes] = await Promise.all([getCategories(), getBrands()])
    categories.value = catRes || []
    brands.value = brandRes || []
  } catch (error) {
    ElMessage.error('加载类别/品牌失败')
  } finally {
    leftLoading.value = false
  }
}

// 切换类别/品牌时重置选中并刷新商品
function onLeftModeChange() {
  selectedId.value = null
  pagination.page = 1
  fetchProducts()
}

function selectLeft(id) {
  selectedId.value = id
  pagination.page = 1
  fetchProducts()
}

// ===== 右侧商品列表 =====
const loading = ref(false)
const products = ref([])
const selectedProducts = ref([])

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const filters = reactive({
  keyword: '',
  status: ''
})

async function fetchProducts() {
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
    // 按左侧选中项过滤
    if (leftMode.value === 'category' && selectedId.value !== null) {
      params.category_id = selectedId.value
    }
    if (leftMode.value === 'brand' && selectedId.value !== null) {
      params.brand_id = selectedId.value
    }

    const response = await getProducts(params)
    products.value = response

    if (!filters.keyword && !filters.status && selectedId.value === null) {
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

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  pagination.page = 1
  fetchProducts()
}

// ===== 对话框 =====
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const productFormRef = ref(null)

const productForm = reactive({
  product_code: '',
  product_name: '',
  product_remark: '',
  status: 'active',
  category_id: null,
  brand_id: null
})

const currentProduct = ref({})

const productRules = {
  product_name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' },
    { min: 2, max: 100, message: '商品名称长度应在2-100字符之间', trigger: 'blur' }
  ],
  product_remark: [
    { max: 500, message: '商品备注不能超过500字符', trigger: 'blur' }
  ]
}

const dialogTitle = computed(() =>
  dialogMode.value === 'create' ? '新建商品' : '编辑商品'
)

function showCreateDialog() {
  dialogMode.value = 'create'
  productForm.product_code = ''
  productForm.product_name = ''
  productForm.product_remark = ''
  productForm.status = 'active'
  productForm.category_id = leftMode.value === 'category' ? selectedId.value : null
  productForm.brand_id = leftMode.value === 'brand' ? selectedId.value : null
  dialogVisible.value = true
}

async function viewProduct(row) {
  try {
    const response = await getProductDetail(row.product_code)
    currentProduct.value = response
    viewDialogVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取商品详情失败')
  }
}

function editProduct(row) {
  dialogMode.value = 'edit'
  productForm.product_code = row.product_code
  productForm.product_name = row.product_name
  productForm.product_remark = row.product_remark || ''
  productForm.status = row.status
  productForm.category_id = row.category_id ?? null
  productForm.brand_id = row.brand_id ?? null
  dialogVisible.value = true
}

async function submitProduct() {
  if (!productFormRef.value) return
  try {
    await productFormRef.value.validate()
    submitting.value = true
    try {
      const data = {
        product_name: productForm.product_name,
        product_remark: productForm.product_remark,
        category_id: productForm.category_id || null,
        brand_id: productForm.brand_id || null
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

function resetForm() {
  productFormRef.value?.resetFields()
  productForm.product_code = ''
  productForm.product_name = ''
  productForm.product_remark = ''
  productForm.status = 'active'
  productForm.category_id = null
  productForm.brand_id = null
}

// ===== 删除 =====
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

function handleSelectionChange(selection) {
  selectedProducts.value = selection
}

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

// ===== 生命周期 =====
onMounted(() => {
  if (canManageProducts.value) {
    loadLeftData()
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

.products-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

/* ===== 左侧面板 ===== */
.left-panel {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.left-header {
  padding: 12px;
  border-bottom: 1px solid #f0f2f5;
  display: flex;
  justify-content: center;
}

.left-list {
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  padding: 6px;
}

.left-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #303133;
  transition: background-color 0.15s;
}

.left-item:hover {
  background-color: #f5f7fa;
}

.left-item.active {
  background-color: #ecf5ff;
  color: #409EFF;
  font-weight: 600;
}

.left-item.indent {
  padding-left: 28px;
  font-size: 12.5px;
  color: #606266;
}

.item-code {
  font-size: 11px;
  color: #a8abb2;
  flex-shrink: 0;
  margin-left: 8px;
}

.left-empty {
  padding: 30px 12px;
  text-align: center;
  color: #a8abb2;
  font-size: 12px;
}

/* ===== 右侧面板 ===== */
.right-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
}

.right-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-spacer {
  flex: 1;
}

.batch-actions {
  margin-bottom: 12px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
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

@media (max-width: 900px) {
  .products-layout {
    flex-direction: column;
  }
  .left-panel {
    width: 100%;
  }
}
</style>
