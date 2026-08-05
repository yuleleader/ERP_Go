<template>
  <div class="orders-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>订单列表</span>
          <el-button type="primary" @click="showCreateDialog" v-if="canCreateOrder">
            新建订单
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="订单状态">
          <el-select v-model="filters.shippingStatus" placeholder="请选择" clearable @change="fetchOrders">
            <el-option label="待发货" value="pending" />
            <el-option label="已发货" value="shipped" />
            <el-option label="虚拟发货" value="virtual" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="追溯码/商品名称" clearable @change="fetchOrders" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchOrders">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="orders" v-loading="loading" style="width: 100%">
        <el-table-column prop="platform_order_no" label="平台订单号" width="180" />
        <el-table-column prop="shop_id" label="网店" width="150" />
        <el-table-column prop="product_name" label="商品名称" />
        <el-table-column prop="sales_amount" label="销售金额" width="100" v-if="!isFactory && !isShipping" />
        <el-table-column prop="commission_amount" label="提成金额" width="100" v-if="!isFactory && !isShipping" />
        <el-table-column prop="shipping_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.shipping_status)">
              {{ getStatusText(row.shipping_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="下单时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="已下单时间" width="100" sortable :sort-method="sortByOrderDays">
          <template #default="{ row }">
            <span :class="{ 'days-warning': calculateOrderDays(row) >= 7, 'days-danger': calculateOrderDays(row) >= 14 }">
              {{ formatOrderDays(row) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="creator_real_name" label="创建人" width="120" />
        <el-table-column prop="shipping_time" label="发货时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.shipping_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewOrder(row)">查看</el-button>
            <el-button link type="primary" size="small" @click="editOrder(row)" v-if="canEditOrder(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="confirmDelete(row)" v-if="canDeleteOrder(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.limit"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchOrders"
        @current-change="fetchOrders"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="900px" @closed="resetForm">
      <el-form ref="orderFormRef" :model="orderForm" :rules="orderRules" label-width="100px">
        <!-- 发货端编辑限制提示 -->
        <el-alert
          v-if="isShipping && dialogMode === 'edit'"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
          title="发货端编辑限制"
          description="发货端仅允许编辑发货状态、物流公司、物流单号，并上传发货凭证；以下字段为只读、禁止修改：收货地址、销售金额、商品名称、发货时间、备注、平台订单号、网店、下单时间。"
        />
        
        <!-- 基本信息区域 -->
        <div class="form-section">
          <div class="section-title">
            <el-icon><FileText /></el-icon>
            <span>基本信息</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="网店" prop="shop_id">
                <el-select v-model="orderForm.shop_id" placeholder="请选择网店" :disabled="dialogMode === 'edit'" @change="onShopChange" class="w-full">
                  <el-option
                    v-for="shop in shops"
                    :key="shop.shop_id"
                    :label="shop.shop_id"
                    :value="shop.shop_id"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="平台订单号" prop="platform_order_no">
                <el-input v-model="orderForm.platform_order_no" placeholder="请输入平台订单号" :disabled="dialogMode === 'edit'" class="w-full" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="订单号" v-if="orderForm.order_id">
                <el-input v-model="orderForm.order_id" disabled class="w-full" />
              </el-form-item>
              <el-form-item v-else>
                <el-tag type="info" class="w-full text-center">订单号将自动生成</el-tag>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="商品名称">
                <el-select 
                  v-model="orderForm.product_name" 
                  placeholder="请选择商品" 
                  class="w-full"
                  filterable
                  default-first-option
                  :disabled="isShipping"
                >
                  <el-option 
                    v-for="product in products" 
                    :key="product.product_code" 
                    :label="product.product_name" 
                    :value="product.product_name"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="销售金额" prop="sales_amount" v-if="!isFactory && !isShipping">
                <el-input v-model="orderForm.sales_amount" type="number" placeholder="请输入销售金额" :min="0" step="0.01" class="w-full" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="状态">
                <el-select v-model="orderForm.shipping_status" placeholder="请选择状态" class="w-full" @change="onStatusChange">
                  <el-option label="未发货" value="pending" />
                  <el-option label="已发货" value="shipped" />
                  <el-option label="虚拟发货" value="virtual" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="发货时间">
                <el-date-picker
                  v-model="orderForm.shipping_time"
                  type="datetime"
                  placeholder="订单发货后自动填充，可手动修改"
                  format="YYYY-MM-DD HH:mm:ss"
                  value-format="YYYY-MM-DD HH:mm:ss"
                  class="w-full"
                  :disabled="isShipping || orderForm.shipping_status !== 'shipped'"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="下单时间">
                <el-date-picker
                  v-model="orderForm.created_at"
                  type="date"
                  placeholder="请选择下单时间（默认今天）"
                  :disabled-date="disabledFutureDate"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  class="w-full"
                  :disabled="isShipping || dialogMode === 'edit'"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item label="收货地址" prop="receiver_address">
                <el-input v-model="orderForm.receiver_address" type="textarea" :rows="2" placeholder="请输入收货地址（含收件人姓名、联系电话、详细地址）" class="w-full" :disabled="isShipping" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item label="备注">
                <el-input v-model="orderForm.remark" type="textarea" :rows="2" placeholder="请输入备注信息" class="w-full" :disabled="isShipping" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 物流信息区域 -->
        <div class="form-section">
          <div class="section-title">
            <el-icon><Truck /></el-icon>
            <span>物流信息</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="发货平台">
                <el-select v-model="orderForm.logistics_company" placeholder="请选择发货平台" class="w-full">
                  <el-option v-for="company in logisticsCompanies" :key="company.id" :label="company.company_name" :value="company.company_name" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="运单号">
                <el-input v-model="orderForm.logistics_no" placeholder="请输入运单号" class="w-full" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 图片上传区域 -->
        <div class="form-section">
          <div class="section-title">
            <el-icon><Image /></el-icon>
            <span>图片上传</span>
          </div>
          
          <!-- 销售端图片 -->
          <div class="image-section">
            <div class="image-header">
              <span class="image-title">📦 商品图片</span>
              <span class="image-desc">（销售端上传，展示商品信息）</span>
            </div>
            <div class="image-upload">
              <el-upload
                class="upload-demo"
                action="/api/images/upload-temp?module=product"
                :headers="uploadHeaders"
                :on-success="createImageUploadHandler('product', 'sales')"
                :on-error="handleImageError"
                :limit="5"
                :file-list="salesProductImages"
                list-type="picture-card"
              >
                <el-icon><Plus /></el-icon>
                <template #tip>
                  <div class="el-upload__tip">最多上传5张商品图片</div>
                </template>
              </el-upload>
            </div>
          </div>

          <!-- 工厂端图片 -->
          <div class="image-section">
            <div class="image-header">
              <span class="image-title">🏭 生产进度图片</span>
              <span class="image-desc">（工厂端上传，展示生产过程）</span>
            </div>
            <div class="image-upload">
              <el-upload
                class="upload-demo"
                action="/api/images/upload-temp?module=production"
                :headers="uploadHeaders"
                :on-success="createImageUploadHandler('production', 'factory')"
                :on-error="handleImageError"
                :limit="5"
                :file-list="factoryProductionImages"
                list-type="picture-card"
              >
                <el-icon><Plus /></el-icon>
                <template #tip>
                  <div class="el-upload__tip">最多上传5张生产进度图片</div>
                </template>
              </el-upload>
            </div>
          </div>

          <!-- 发货端图片 -->
          <div class="image-section">
            <div class="image-header">
              <span class="image-title">📤 发货凭证图片</span>
              <span class="image-desc">（发货端上传，展示发货信息）</span>
            </div>
            <div class="image-upload">
              <el-upload
                class="upload-demo"
                action="/api/images/upload-temp?module=shipping"
                :headers="uploadHeaders"
                :on-success="createImageUploadHandler('shipping', 'shipping')"
                :on-error="handleImageError"
                :limit="5"
                :file-list="shippingDeliveryImages"
                list-type="picture-card"
              >
                <el-icon><Plus /></el-icon>
                <template #tip>
                  <div class="el-upload__tip">最多上传5张发货凭证图片</div>
                </template>
              </el-upload>
            </div>
          </div>
        </div>

      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitOrder" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteDialogVisible" title="删除订单" width="400px">
      <el-form ref="deleteFormRef" :model="deleteForm" :rules="deleteRules" label-width="100px">
        <el-form-item label="密码" prop="password">
          <el-input v-model="deleteForm.password" type="password" placeholder="请输入当前登录账号的密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleDeleteOrder" :loading="deleting">确认删除</el-button>
      </template>
    </el-dialog>

    <!-- 订单详情弹窗（与智慧大屏共用，按 orderId 加载完整详情） -->
    <OrderDetailDialog v-model="viewDialogVisible" :order-id="viewingOrderId" />
  </div>
</template>

<script setup>
import { formatDate, formatDateTime, toBeijingDate } from '@/utils/format'
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { getOrders, createOrder, updateOrder, deleteOrder, getOrder } from '@/api/order'
import { getShops } from '@/api/shop'
import { migrateImage } from '@/api/image'
import { getLogisticsCompanies } from '@/api/logistics'
import { getProducts } from '@/api/product'
import { authImageUrl } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import OrderDetailDialog from '@/components/OrderDetailDialog.vue'
// QRCode will be imported dynamically

const userStore = useUserStore()

const loading = ref(false)
const orders = ref([])
const shops = ref([])
const logisticsCompanies = ref([])
const products = ref([])  // 商品列表
const uploadHeaders = ref({})
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const viewingOrderId = ref('')

const deleteDialogVisible = ref(false)
const dialogMode = ref('create')
const submitting = ref(false)
const deleting = ref(false)

// 图片相关变量
// 销售端图片
const salesProductImages = ref([])
// 工厂端图片
const factoryProductionImages = ref([])
// 发货端图片
const shippingDeliveryImages = ref([])
const tempImages = ref([])

const orderFormRef = ref(null)
const orderForm = reactive({
  shop_id: '',
  platform_order_no: '',
  product_name: '',
  sales_amount: '',
  receiver_address: '',
  remark: '',
  logistics_company: '',
  logistics_no: '',
  shipping_status: 'pending',
  shipping_time: '',
  created_at: ''
})

const orderRules = {
  shop_id: [{ required: true, message: '请选择网店', trigger: 'change' }],
  platform_order_no: [{ required: true, message: '请输入平台订单号', trigger: 'blur' }]
}

const filters = reactive({
  shippingStatus: '',
  keyword: ''
})

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})


/**
 * 计算已下单天数
 * 仅当订单状态为"待发货"(pending)或"虚拟发货"(virtual)时显示
 * 其他状态返回空值
 * @param {Object} row - 订单行数据
 * @returns {Number|null} - 天数差或null
 */
function calculateOrderDays(row) {
  // 仅对"待发货"和"虚拟发货"状态计算天数
  if (row.shipping_status !== 'pending' && row.shipping_status !== 'virtual') {
    return null
  }
  
  if (!row.created_at) {
    return null
  }
  
  // 获取下单时间（按北京时间解析，避免浏览器时区偏差）
  const orderDate = toBeijingDate(row.created_at) || new Date()
  // 获取当前时间
  const currentDate = new Date()
  
  // 计算时间差（毫秒）
  const timeDiff = currentDate.getTime() - orderDate.getTime()
  
  // 转换为天数（向下取整）
  const daysDiff = Math.floor(timeDiff / (1000 * 60 * 60 * 24))
  
  // 确保返回正数或0
  return Math.max(0, daysDiff)
}

/**
 * 格式化已下单天数显示
 * @param {Object} row - 订单行数据
 * @returns {String} - 格式化后的天数显示
 */
function formatOrderDays(row) {
  const days = calculateOrderDays(row)
  if (days === null) {
    return ''
  }
  return `${days}天`
}

/**
 * 排序方法：按已下单天数排序
 * 支持升序和降序排列
 * @param {Object} a - 第一行数据
 * @param {Object} b - 第二行数据
 * @returns {Number} - 排序结果
 */
function sortByOrderDays(a, b) {
  const daysA = calculateOrderDays(a)
  const daysB = calculateOrderDays(b)
  
  // null值排在最后
  if (daysA === null && daysB === null) return 0
  if (daysA === null) return 1
  if (daysB === null) return -1
  
  return daysA - daysB
}

const currentOrder = ref({})
const currentDeleteOrder = ref(null)

// 删除订单相关变量
const deleteForm = reactive({
  password: ''
})
const deleteRules = {
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}
const deleteFormRef = ref(null)

const isFactory = computed(() => userStore.role === 'factory')
const isShipping = computed(() => userStore.role === 'shipping')
const canCreateOrder = computed(() => ['boss', 'sales'].includes(userStore.role))
const canEditOrder = (row) => {
  if (userStore.role === 'boss') return true
  if (userStore.role === 'shipping') return true
  if (userStore.role === 'sales' && String(row.created_by) === String(userStore.userInfo?.username)) return true
  return false
}
const canDeleteOrder = (row) => {
  // 仅订单创建人可以删除订单
  return String(row.created_by) === String(userStore.userInfo?.username)
}

function getStatusType(status) {
  return { pending: 'warning', shipped: 'success', virtual: 'info' }[status] || ''
}

function getStatusText(status) {
  return { pending: '待发货', shipped: '已发货', virtual: '虚拟发货' }[status] || status
}

async function fetchOrders() {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit
    }
    if (filters.shippingStatus) params.shipping_status = filters.shippingStatus
    if (filters.keyword) params.keyword = filters.keyword

    const response = await getOrders(params)
    orders.value = response.data || response
  } catch (error) {
    ElMessage.error('获取订单列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchShops() {
  try {
    shops.value = await getShops()
  } catch (error) {
    console.error('获取网店列表失败:', error)
  }
}

async function fetchLogisticsCompanies() {
  try {
    logisticsCompanies.value = await getLogisticsCompanies()
  } catch (error) {
    console.error('获取物流公司列表失败:', error)
  }
}

/**
 * 获取商品列表
 * 用于订单创建时的商品名称选择
 */
async function fetchProducts() {
  try {
    const response = await getProducts({ limit: 100 })
    products.value = response
  } catch (error) {
    console.error('获取商品列表失败:', error)
  }
}

async function onShopChange(shopId) {
  // 创建订单时不需要生成二维码，移除相关逻辑
}

function showCreateDialog() {
  dialogMode.value = 'create'
  // 设置默认日期为今天
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  orderForm.created_at = `${year}-${month}-${day}`
  dialogVisible.value = true
}

// 禁用未来日期
function disabledFutureDate(time) {
  return time.getTime() > Date.now()
}

async function viewOrder(row) {
  // 共用订单详情弹窗：按 orderId 加载完整详情（含图片/二维码）
  viewingOrderId.value = row.order_id
  viewDialogVisible.value = true
}

async function editOrder(row) {
  // 重新从后端拉取最新订单数据，避免沿用列表缓存的旧值（如手机端已修改）
  try {
    const res = await getOrder(row.order_id)
    row = res?.data || res || row
  } catch (e) {
    console.error('获取订单最新数据失败，使用列表缓存:', e)
  }
  currentOrder.value = row
  dialogMode.value = 'edit'
  orderForm.shop_id = row.shop_id
  orderForm.platform_order_no = row.platform_order_no
  orderForm.product_name = row.product_name
  orderForm.sales_amount = row.sales_amount || ''
  orderForm.receiver_address = row.receiver_address
  orderForm.remark = row.remark
  orderForm.logistics_company = row.logistics_company || ''
  orderForm.logistics_no = row.logistics_no || ''
  orderForm.shipping_status = row.shipping_status || 'pending'
  // 设置发货时间（从ISO格式转换为日期时间格式）
  if (row.shipping_time) {
    const d = new Date(row.shipping_time)
    if (!isNaN(d.getTime())) {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      const h = String(d.getHours()).padStart(2, '0')
      const min = String(d.getMinutes()).padStart(2, '0')
      const s = String(d.getSeconds()).padStart(2, '0')
      orderForm.shipping_time = `${year}-${month}-${day} ${h}:${min}:${s}`
    } else {
      orderForm.shipping_time = ''
    }
  } else {
    orderForm.shipping_time = ''
  }
  // 设置下单时间（从ISO格式转换为日期格式）
  if (row.created_at) {
    orderForm.created_at = row.created_at.split('T')[0]
  } else {
    orderForm.created_at = ''
  }
  dialogVisible.value = true
}

/**
 * 当订单状态变更时，自动填充/清空发货时间
 */
function onStatusChange(status) {
  if (status === 'shipped' && !orderForm.shipping_time) {
    // 状态变更为已发货且无发货时间时，自动填充当前时间
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const h = String(now.getHours()).padStart(2, '0')
    const min = String(now.getMinutes()).padStart(2, '0')
    const s = String(now.getSeconds()).padStart(2, '0')
    orderForm.shipping_time = `${year}-${month}-${day} ${h}:${min}:${s}`
  } else if (status !== 'shipped') {
    // 状态改为非已发货时，清空发货时间
    orderForm.shipping_time = ''
  }
}

// 处理图片上传成功（使用工厂函数创建带image_type和layer的处理器）
function createImageUploadHandler(imageType, layer) {
  return async function(response, uploadFile) {
    if (response && response.temp_id) {
      const tempId = response.temp_id
      
      // 保存临时图片信息（包含层级）
      tempImages.value.push({
        temp_id: tempId,
        image_type: imageType,
        layer: layer
      })
    
    // 根据层级和图片类型添加到对应的文件列表
    if (layer === 'sales') {
      salesProductImages.value.push({
        name: uploadFile.name,
        url: authImageUrl(response.image_url),
        temp_id: tempId
      })
    } else if (layer === 'factory') {
      factoryProductionImages.value.push({
        name: uploadFile.name,
        url: authImageUrl(response.image_url),
        temp_id: tempId
      })
    } else if (layer === 'shipping') {
      shippingDeliveryImages.value.push({
        name: uploadFile.name,
        url: authImageUrl(response.image_url),
        temp_id: tempId
      })
    }
    } else {
      ElMessage.error('上传失败，请重试')
    }
  }
}

// 处理图片上传失败
function handleImageError(error) {
  ElMessage.error('上传失败，请重试')
}

async function submitOrder() {
  if (!orderFormRef.value) return

  await orderFormRef.value.validate(async (valid) => {
    if (valid) {
        submitting.value = true
        try {
          // 发货端仅允许提交发货状态、物流公司、物流单号，其余字段不发送
          const data = userStore.role === 'shipping'
            ? {
                shipping_status: orderForm.shipping_status,
                logistics_company: orderForm.logistics_company,
                logistics_no: orderForm.logistics_no
              }
            : {
                shop_id: orderForm.shop_id,
                platform_order_no: orderForm.platform_order_no,
                product_name: orderForm.product_name,
                sales_amount: orderForm.sales_amount,
                receiver_address: orderForm.receiver_address,
                remark: orderForm.remark,
                logistics_company: orderForm.logistics_company,
                logistics_no: orderForm.logistics_no,
                shipping_status: orderForm.shipping_status,
                shipping_time: orderForm.shipping_time || null
              }

        let orderId
        if (dialogMode.value === 'create') {
          const result = await createOrder(data)
          orderId = result.order_id
          ElMessage.success('订单创建成功')
        } else {
          orderId = currentOrder.value.order_id
          await updateOrder(orderId, data)
          ElMessage.success('订单更新成功')
        }

        // 迁移临时图片到正式目录
        for (const tempImage of tempImages.value) {
          try {
            await migrateImage(tempImage.temp_id, orderId)
          } catch (error) {
            console.error('迁移图片失败:', error)
          }
        }

        dialogVisible.value = false
        fetchOrders()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '操作失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

function resetForm() {
  orderFormRef.value?.resetFields()
  orderForm.shop_id = ''
  orderForm.platform_order_no = ''
  orderForm.product_name = ''
  orderForm.sales_amount = ''
  orderForm.receiver_address = ''
  orderForm.remark = ''
  orderForm.logistics_company = ''
  orderForm.logistics_no = ''
  orderForm.shipping_status = 'pending'
  orderForm.shipping_time = ''
  orderForm.created_at = ''
  
  // 清空图片相关变量（按层级分类）
  salesProductImages.value = []
  factoryProductionImages.value = []
  shippingDeliveryImages.value = []
  tempImages.value = []
}

function confirmDelete(row) {
  currentDeleteOrder.value = row
  deleteForm.password = ''
  deleteDialogVisible.value = true
}

async function handleDeleteOrder() {
  if (!deleteFormRef.value) return
  
  try {
    await deleteFormRef.value.validate()
    deleting.value = true
    
    await deleteOrder(currentDeleteOrder.value.order_id, deleteForm.password)
    ElMessage.success('订单删除成功')
    deleteDialogVisible.value = false
    await fetchOrders()
  } catch (error) {
    if (error.response && error.response.data && error.response.data.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error('删除订单失败')
    }
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  // 先加载用户信息，这对权限判断很重要
  if (userStore.token && !userStore.userInfo) {
    await userStore.fetchUserInfo()
  }
  
  fetchOrders()
  if (canCreateOrder.value) {
    fetchShops()
    fetchLogisticsCompanies()
    fetchProducts()  // 获取商品列表
  }
  const token = localStorage.getItem('token')
  if (token) {
    uploadHeaders.value = {
      Authorization: `Bearer ${token}`
    }
  }
})
</script>

<style scoped>
.orders-container {
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

.filter-form .el-select {
  width: 150px;
}

.filter-form .el-select .el-input__wrapper {
  padding-right: 30px;
}

.filter-form .el-select-dropdown__item {
  height: 40px;
  line-height: 40px;
  padding: 0 16px;
}

.upload-container {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  border: 1px dashed #d9d9d9;
  border-radius: 4px;
  background-color: #fafafa;
}

.upload-tip {
  color: #999;
  font-size: 12px;
}

/* 表单区域样式 */
.form-section {
  margin-bottom: 24px;
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.form-section:last-of-type {
  margin-bottom: 0;
}

/* 区域标题样式 */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8e8e8;
}

/* 图片标签页激活状态 */
.active-tab {
  color: #409EFF !important;
  font-weight: 600;
  border-bottom: 2px solid #409EFF;
}

.section-title el-icon {
  font-size: 18px;
  color: #409eff;
}

/* 图片区域样式 */
.image-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
}

.image-section:last-of-type {
  margin-bottom: 0;
}

/* 图片区域标题 */
.image-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.image-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.image-desc {
  font-size: 12px;
  color: #999;
}

/* 图片上传容器 */
.image-upload {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* 表单元素宽度 */
.w-full {
  width: 100%;
}

/* 已下单时间警告样式 */
.days-warning {
  color: #e6a23c;
  font-weight: bold;
}

.days-danger {
  color: #f56c6c;
  font-weight: bold;
}
</style>
