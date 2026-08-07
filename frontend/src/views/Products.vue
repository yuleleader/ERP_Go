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
          <el-button v-if="canCreateProducts" type="primary" @click="showCreateDialog">新建商品</el-button>
        </div>

        <div class="batch-actions" v-if="canDeleteProducts && selectedProducts.length > 0">
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
          <el-table-column v-if="canDeleteProducts" type="selection" width="45" />
          <el-table-column prop="product_code" label="商品编码" width="130" />
          <el-table-column prop="product_name" label="商品名称" min-width="160" />
          <el-table-column label="类别" width="120">
            <template #default="{ row }">
              {{ categoryName(row.category_id) }}
            </template>
          </el-table-column>
          <el-table-column label="品牌" width="110">
            <template #default="{ row }">
              {{ brandName(row.brand_id) }}
            </template>
          </el-table-column>
          <el-table-column label="售价" width="100">
            <template #default="{ row }">
              <span v-if="row.retail_price != null">¥{{ Number(row.retail_price).toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="图片" width="60" align="center">
            <template #default="{ row }">
              <el-image
                v-if="row.image_count"
                :src="imageUrlWithToken(row.cover_image)"
                :preview-src-list="row.preview_urls || []"
                fit="cover"
                style="width: 36px; height: 36px; border-radius: 4px;"
                :preview-teleported="true"
              />
              <span v-else style="color: #c0c4cc;">—</span>
            </template>
          </el-table-column>
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
              <el-button v-if="canEditProducts" link type="primary" size="small" @click="editProduct(row)">编辑</el-button>
              <el-button v-if="canDeleteProducts" link type="danger" size="small" @click="handleDeleteProduct(row)">删除</el-button>
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

    <!-- 创建/编辑商品对话框（表格风格） -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="960px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <div class="product-form-table" v-loading="dialogLoading">
        <table class="form-table" cellspacing="0" cellpadding="0">
          <tbody>
            <tr>
              <th class="th-label">商品编码</th>
              <td class="td-value" :class="{ readonly: dialogMode === 'edit' }">
                <el-input
                  v-if="dialogMode === 'edit'"
                  v-model="productForm.product_code"
                  disabled
                />
                <span v-else class="placeholder">保存后自动生成 PLU-000xxx</span>
              </td>
              <th class="th-label">商品名称</th>
              <td class="td-value">
                <el-input v-model="productForm.product_name" placeholder="商品名称" maxlength="100" show-word-limit />
              </td>
              <td class="td-image-cell" rowspan="9">
                <div class="image-upload-area">
                  <div class="image-upload-title">商品图片（上传）</div>
                  <el-upload
                    v-if="dialogMode === 'edit' && !!savedProductCode"
                    list-type="picture-card"
                    :limit="5"
                    :file-list="imageFileList"
                    :on-exceed="onImageExceed"
                    :on-remove="handleImageRemove"
                    :on-preview="handleUploadPreview"
                    :http-request="customUpload"
                    :disabled="imageUploading"
                  >
                    <el-icon><Plus /></el-icon>
                  </el-upload>
                  <div v-else class="image-upload-hint">
                    请先保存商品基本信息后再上传图片
                  </div>
                  <div class="image-upload-tip">最多 5 张（jpg / jpeg / png，≤ 5MB）</div>
                </div>
              </td>
            </tr>

            <tr>
              <th class="th-label">类别</th>
              <td class="td-value">
                <el-select v-model="productForm.category_id" placeholder="请选择" clearable filterable style="width: 100%;">
                  <el-option
                    v-for="cat in categoryFlat"
                    :key="cat.id"
                    :label="catLevelLabel(cat)"
                    :value="cat.id"
                  />
                </el-select>
              </td>
              <th class="th-label">品牌</th>
              <td class="td-value">
                <el-select v-model="productForm.brand_id" placeholder="请选择" clearable filterable style="width: 100%;">
                  <el-option
                    v-for="b in brands"
                    :key="b.id"
                    :label="`${b.brand_name}（${b.brand_code}）`"
                    :value="b.id"
                  />
                </el-select>
              </td>
            </tr>

            <tr>
              <th class="th-label">成本价</th>
              <td class="td-value">
                <el-input-number v-model="productForm.cost_price" :min="0" :precision="2" :controls="false" style="width: 100%;" placeholder="0.00" />
              </td>
              <th class="th-label">零售价</th>
              <td class="td-value">
                <el-input-number v-model="productForm.retail_price" :min="0" :precision="2" :controls="false" style="width: 100%;" placeholder="0.00" />
              </td>
            </tr>

            <tr>
              <th class="th-label">最低售价</th>
              <td class="td-value" colspan="3">
                <el-input-number v-model="productForm.min_price" :min="0" :precision="2" :controls="false" style="width: 200px;" placeholder="0.00" />
              </td>
            </tr>

            <tr>
              <th class="th-label">备注1</th>
              <td class="td-value" colspan="3">
                <el-input v-model="productForm.remark1" maxlength="500" show-word-limit />
              </td>
            </tr>

            <tr>
              <th class="th-label">备注2</th>
              <td class="td-value" colspan="3">
                <el-input v-model="productForm.remark2" maxlength="500" show-word-limit />
              </td>
            </tr>

            <tr>
              <th class="th-label">备注3</th>
              <td class="td-value" colspan="3">
                <el-input v-model="productForm.remark3" maxlength="500" show-word-limit />
              </td>
            </tr>

            <tr>
              <th class="th-label">商品备注</th>
              <td class="td-value" colspan="3">
                <el-input v-model="productForm.product_remark" type="textarea" :rows="3" maxlength="500" show-word-limit />
              </td>
            </tr>

            <tr>
              <th class="th-label">商品状态</th>
              <td class="td-value" colspan="3">
                <el-radio-group v-model="productForm.status">
                  <el-radio-button label="active">启用</el-radio-button>
                  <el-radio-button label="inactive">停用</el-radio-button>
                </el-radio-group>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitProduct" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 商品详情对话框（表格风格） -->
    <el-dialog v-model="viewDialogVisible" title="查看商品档案" width="900px">
      <div class="product-view-table">
        <table class="form-table" cellspacing="0" cellpadding="0">
          <tbody>
            <tr>
              <th class="th-label">商品编码</th>
              <td class="td-value">{{ currentProduct.product_code }}</td>
              <th class="th-label">商品名称</th>
              <td class="td-value">{{ currentProduct.product_name }}</td>
              <td class="td-image-cell" rowspan="5">
                <div class="image-upload-area">
                  <div class="image-upload-title">商品图片</div>
                  <div class="image-grid">
                    <div
                      v-for="idx in 5"
                      :key="idx"
                      class="image-slot"
                    >
                      <el-image
                        v-if="currentProductImages[idx - 1]"
                        :src="imageUrlWithToken(currentProductImages[idx - 1].image_url)"
                        :preview-src-list="previewableImageUrls(currentProductImages)"
                        :preview-teleported="true"
                        fit="cover"
                      />
                      <span v-else class="empty-slot">空位 {{ idx }}</span>
                    </div>
                  </div>
                  <div class="image-upload-tip">最多 5 张，点击可预览</div>
                </div>
              </td>
            </tr>
            <tr>
              <th class="th-label">类别</th>
              <td class="td-value">{{ categoryName(currentProduct.category_id) || '未设置' }}</td>
              <th class="th-label">品牌</th>
              <td class="td-value">{{ brandName(currentProduct.brand_id) || '未设置' }}</td>
            </tr>
            <tr>
              <th class="th-label">成本价</th>
              <td class="td-value">¥{{ Number(currentProduct.cost_price || 0).toFixed(2) }}</td>
              <th class="th-label">零售价</th>
              <td class="td-value">¥{{ Number(currentProduct.retail_price || 0).toFixed(2) }}</td>
            </tr>
            <tr>
              <th class="th-label">最低售价</th>
              <td class="td-value" colspan="3">¥{{ Number(currentProduct.min_price || 0).toFixed(2) }}</td>
            </tr>
            <tr>
              <th class="th-label">备注1</th>
              <td class="td-value" colspan="3">{{ currentProduct.remark1 || '—' }}</td>
            </tr>
            <tr>
              <th class="th-label">备注2</th>
              <td class="td-value" colspan="3">{{ currentProduct.remark2 || '—' }}</td>
            </tr>
            <tr>
              <th class="th-label">备注3</th>
              <td class="td-value" colspan="3">{{ currentProduct.remark3 || '—' }}</td>
            </tr>
            <tr>
              <th class="th-label">商品备注</th>
              <td class="td-value" colspan="3">
                <div class="remark-content">{{ currentProduct.product_remark || '暂无备注' }}</div>
              </td>
            </tr>
            <tr>
              <th class="th-label">创建时间</th>
              <td class="td-value" colspan="3">{{ formatDateTime(currentProduct.created_at) }}</td>
            </tr>
            <tr>
              <th class="th-label">修改时间</th>
              <td class="td-value" colspan="3">{{ formatDateTime(currentProduct.updated_at) }}</td>
            </tr>
            <tr>
              <th class="th-label">商品状态</th>
              <td class="td-value" colspan="3">
                <el-tag :type="currentProduct.status === 'active' ? 'success' : 'info'">
                  {{ currentProduct.status === 'active' ? '启用' : '停用' }}
                </el-tag>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </el-dialog>

    <!-- 上传区图片大图预览 -->
    <el-image-viewer
      v-if="uploadPreviewVisible"
      :url-list="uploadPreviewList"
      :initial-index="uploadPreviewIndex"
      @close="uploadPreviewVisible = false"
    />
  </div>
</template>

<script setup>
/**
 * 商品管理页面（主从布局 + 表格风格新建/编辑对话框 + 商品图片上传）
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
  getProductCount,
  uploadProductImage,
  getProductImages,
  deleteProductImage
} from '@/api/product'
import { getCategories } from '@/api/category'
import { getBrands } from '@/api/brand'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { imageUrlWithToken } from '@/utils/imageUrl'
import { Plus } from '@element-plus/icons-vue'

const userStore = useUserStore()

// 商品管理对所有人员开放查看
const canManageProducts = computed(() => true)
// 仅老板端/销售端可编辑、上传图片
const canEditProducts = computed(() => ['boss', 'sales'].includes(userStore.userInfo?.role))
// 仅老板端可新建商品
const canCreateProducts = computed(() => userStore.userInfo?.role === 'boss')
// 仅老板端可删除（单选/批量）
const canDeleteProducts = computed(() => userStore.userInfo?.role === 'boss')

// ===== 左侧导航 =====
const leftMode = ref('category')
const selectedId = ref(null)
const leftLoading = ref(false)
const categories = ref([])
const brands = ref([])

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
    if (leftMode.value === 'category' && selectedId.value !== null) {
      params.category_id = selectedId.value
    }
    if (leftMode.value === 'brand' && selectedId.value !== null) {
      params.brand_id = selectedId.value
    }

    const list = await getProducts(params)
    // 为每条商品加载首张图片用于列表缩略图
    const enriched = await Promise.all((list || []).map(async (p) => {
      try {
        const imgs = await getProductImages(p.product_code)
        const items = imgs.data || []
        const preview_urls = items.map((i) => imageUrlWithToken(i.image_url))
        return {
          ...p,
          image_count: items.length,
          cover_image: items[0]?.image_url || '',
          preview_urls
        }
      } catch (e) {
        return { ...p, image_count: 0, cover_image: '', preview_urls: [] }
      }
    }))
    products.value = enriched

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
const dialogLoading = ref(false)

// 保存后返回的 product_code（用于编辑模式上传图片）
const savedProductCode = ref('')

// 图片上传（el-upload）
const imageFileList = ref([])
const imageUploading = ref(false)

const productForm = reactive({
  product_code: '',
  product_name: '',
  product_remark: '',
  status: 'active',
  category_id: null,
  brand_id: null,
  cost_price: null,
  retail_price: null,
  min_price: null,
  remark1: '',
  remark2: '',
  remark3: ''
})

const currentProduct = ref({})
const currentProductImages = ref([])

const dialogTitle = computed(() =>
  dialogMode.value === 'create' ? '新建商品档案' : '编辑商品档案'
)

function showCreateDialog() {
  dialogMode.value = 'create'
  savedProductCode.value = ''
  imageFileList.value = []
  Object.assign(productForm, {
    product_code: '',
    product_name: '',
    product_remark: '',
    status: 'active',
    category_id: leftMode.value === 'category' ? selectedId.value : null,
    brand_id: leftMode.value === 'brand' ? selectedId.value : null,
    cost_price: null,
    retail_price: null,
    min_price: null,
    remark1: '',
    remark2: '',
    remark3: ''
  })
  dialogVisible.value = true
}

async function viewProduct(row) {
  try {
    const res = await getProductDetail(row.product_code)
    currentProduct.value = res
    const imgs = await getProductImages(row.product_code)
    currentProductImages.value = imgs.data || []
    viewDialogVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取商品详情失败')
  }
}

function previewableImageUrls(items) {
  return items.map((i) => imageUrlWithToken(i.image_url))
}

async function editProduct(row) {
  dialogMode.value = 'edit'
  try {
    const res = await getProductDetail(row.product_code)
    Object.assign(productForm, {
      product_code: res.product_code,
      product_name: res.product_name,
      product_remark: res.product_remark || '',
      status: res.status || 'active',
      category_id: res.category_id ?? null,
      brand_id: res.brand_id ?? null,
      cost_price: res.cost_price ?? null,
      retail_price: res.retail_price ?? null,
      min_price: res.min_price ?? null,
      remark1: res.remark1 || '',
      remark2: res.remark2 || '',
      remark3: res.remark3 || ''
    })
    savedProductCode.value = res.product_code
    const imgs = await getProductImages(res.product_code)
    imageFileList.value = (imgs.data || []).map((i) => ({
      id: i.id,
      name: i.file_name,
      url: imageUrlWithToken(i.image_url)
    }))
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载商品失败')
  }
}

async function submitProduct() {
  if (!productForm.product_name || productForm.product_name.length < 2) {
    ElMessage.warning('请填写商品名称（2-100 字符）')
    return
  }
  submitting.value = true
  try {
    const payload = {
      product_name: productForm.product_name,
      product_remark: productForm.product_remark,
      category_id: productForm.category_id || null,
      brand_id: productForm.brand_id || null,
      cost_price: productForm.cost_price ?? null,
      retail_price: productForm.retail_price ?? null,
      min_price: productForm.min_price ?? null,
      remark1: productForm.remark1 || '',
      remark2: productForm.remark2 || '',
      remark3: productForm.remark3 || ''
    }
    let saved
    if (dialogMode.value === 'create') {
      saved = await createProduct(payload)
      savedProductCode.value = saved.product_code
      ElMessage.success('商品创建成功，现在可以上传图片了')
      dialogMode.value = 'edit'
      productForm.product_code = saved.product_code
      // 关闭后允许再次打开做图片上传
    } else {
      payload.status = productForm.status
      saved = await updateProduct(productForm.product_code, payload)
      ElMessage.success('商品更新成功')
    }
    dialogVisible.value = false
    fetchProducts()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(productForm, {
    product_code: '',
    product_name: '',
    product_remark: '',
    status: 'active',
    category_id: null,
    brand_id: null,
    cost_price: null,
    retail_price: null,
    min_price: null,
    remark1: '',
    remark2: '',
    remark3: ''
  })
  imageFileList.value = []
  savedProductCode.value = ''
}

// ===== 图片上传（自定义 http-request） =====
const uploadPreviewVisible = ref(false)
const uploadPreviewList = ref([])
const uploadPreviewIndex = ref(0)

// 点击上传区缩略图 → 打开大图预览（支持左右切换/退出）
function handleUploadPreview(file) {
  const urls = imageFileList.value.map((f) => f.url)
  const idx = imageFileList.value.findIndex(
    (f) => (file.uid && f.uid === file.uid) || (file.name && f.name === file.name)
  )
  uploadPreviewList.value = urls
  uploadPreviewIndex.value = Math.max(0, idx)
  uploadPreviewVisible.value = true
}

function onImageExceed() {
  ElMessage.warning('每个商品最多上传 5 张图片')
}

function customUpload(option) {
  if (!savedProductCode.value) {
    ElMessage.warning('请先保存商品基本信息')
    return
  }
  imageUploading.value = true
  uploadProductImage(savedProductCode.value, option.file)
    .then((res) => {
      const item = {
        id: res.id,
        name: res.file_name,
        url: imageUrlWithToken(res.image_url)
      }
      imageFileList.value = [...imageFileList.value, item]
      option.onSuccess(res)
      ElMessage.success('图片上传成功')
    })
    .catch((err) => {
      option.onError(err)
      ElMessage.error(err.response?.data?.detail || '图片上传失败')
    })
    .finally(() => {
      imageUploading.value = false
    })
}

async function handleImageRemove(file) {
  if (!file || !file.id) {
    // 浏览器原生 File 对象（刚选未上传），直接从列表中移除即可
    return true
  }
  try {
    await deleteProductImage(file.id)
    imageFileList.value = imageFileList.value.filter((f) => f.id !== file.id)
    ElMessage.success('图片已删除')
    return true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
    return false
  }
}

// ===== 删除商品 =====
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

.image-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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

/* ===== 查看商品档案：图片预览网格 ===== */
.product-view-table {
  padding: 4px 8px;
  max-height: 65vh;
  overflow-y: auto;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  width: 100%;
}

.image-slot {
  width: 100%;
  height: 80px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.image-slot .el-image {
  width: 100%;
  height: 100%;
}

.empty-slot {
  font-size: 11px;
  color: #c0c4cc;
}

/* ===== 表格风格表单 ===== */
.product-form-table {
  padding: 4px 8px;
  max-height: 60vh;
  overflow-y: auto;
}

.form-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 13px;
}

.form-table th,
.form-table td {
  border: 1px solid #dcdfe6;
  padding: 6px 10px;
  vertical-align: middle;
}

.form-table .th-label {
  width: 80px;
  background: #f7f8fa;
  text-align: center;
  color: #606266;
  font-weight: 500;
}

.form-table .td-value {
  background: #fff;
  color: #303133;
}

.form-table .td-value.readonly {
  background: #fafafa;
  color: #909399;
}

.form-table .placeholder {
  color: #c0c4cc;
  font-size: 12px;
}

.td-image-cell {
  background: #f7f8fa;
  vertical-align: top;
  padding: 12px;
  width: 220px;
}

.image-upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.image-upload-title {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
}

.image-upload-tip {
  font-size: 12px;
  color: #909399;
  text-align: center;
}

.image-upload-hint {
  font-size: 12px;
  color: #c0c4cc;
  text-align: center;
  padding: 30px 10px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  width: 100%;
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