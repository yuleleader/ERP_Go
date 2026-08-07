<template>
  <el-dialog v-model="visible" width="950px" @closed="handleClosed">
    <!-- 顶部导航栏 -->
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
        <el-button
          type="text"
          @click="visible = false"
          style="font-size: 14px; padding: 0;"
        >
          ← 返回订单列表
        </el-button>
        <span style="font-size: 16px; font-weight: bold;">订单详情</span>
        <span></span>
      </div>
    </template>

    <div v-loading="loading" element-loading-text="加载中...">
      <!-- 核心信息区：左右分栏 -->
      <div style="display: flex; gap: 25px; margin-bottom: 25px;">
        <!-- 左侧：基础信息 -->
        <div style="flex: 1; border: 1px solid #eee; border-radius: 8px; padding: 24px;">
          <div class="detail-info-row">
            <span class="detail-label" style="text-align: left; text-align-last: auto;">平台订单号</span>
            <span class="detail-value" style="font-weight: 600; font-size: 15px;">{{ order.platform_order_no || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">网店</span>
            <span class="detail-value">{{ order.shop_id || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">商品名称</span>
            <span class="detail-value">{{ order.product_name || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">销售金额</span>
            <span class="detail-value">{{ order.sales_amount || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">下单时间</span>
            <span class="detail-value">{{ order.created_at ? String(order.created_at).split('T')[0] : '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">创建人</span>
            <span class="detail-value">{{ order.creator_real_name || '——' }}</span>
          </div>
          <div class="detail-info-row" style="align-items: flex-start;">
            <span class="detail-label">收货地址</span>
            <span class="detail-value">{{ order.receiver_address || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">物流公司</span>
            <span class="detail-value">{{ order.logistics_company || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">运单号1</span>
            <span class="detail-value">{{ order.logistics_no || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">运单号2</span>
            <span class="detail-value">{{ order.logistics_no_2 || '——' }}</span>
          </div>
          <div class="detail-info-row">
            <span class="detail-label">运费</span>
            <span class="detail-value">{{ order.freight || '——' }}</span>
          </div>
          <div class="detail-info-row" style="align-items: flex-start;">
            <span class="detail-label">备注</span>
            <span class="detail-value">{{ order.remark || '——' }}</span>
          </div>
        </div>

        <!-- 右侧：二维码 + 发货状态 + 生产进度 -->
        <div style="width: 180px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px;">
          <div style="border: 1px solid #eee; border-radius: 8px; padding: 15px; text-align: center;">
            <img
              :src="qrCodeUrl"
              alt="订单二维码"
              style="width: 130px; height: 130px; margin-bottom: 10px;"
            />
            <div style="padding-top: 10px; border-top: 1px dashed #eee;">
              <span style="font-size: 12px; color: #666;">发货状态：</span>
              <el-tag :type="getStatusType(order.shipping_status)" size="small">
                {{ getStatusText(order.shipping_status) }}
              </el-tag>
            </div>
          </div>

          <!-- 生产进度 -->
          <div style="border: 1px solid #eee; border-radius: 8px; padding: 15px;">
            <div style="font-size: 13px; font-weight: 600; margin-bottom: 10px; color: #333;">生产进度</div>
            <div style="margin-bottom: 8px;">
              <el-tag :type="getProduceStatusType(order.produce_status)" size="small">
                {{ getProduceStatusText(order.produce_status) }}
              </el-tag>
            </div>
            <div v-if="order.produce_status_update_at" style="font-size: 11px; color: #999; margin-bottom: 10px;">
              {{ formatDateTime(order.produce_status_update_at) }}
              <span v-if="order.produce_status_update_user"> · {{ order.produce_status_update_user }}</span>
            </div>
            <el-select
              v-model="selectedProduceStatus"
              placeholder="修改状态"
              size="small"
              style="width: 100%;"
              @change="handleUpdateProduceStatus"
            >
              <el-option label="未生产" value="unproduce" />
              <el-option label="生产中" value="producing" />
              <el-option label="生产完成" value="produced" />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 图片预览区：标签页 + 纯展示 -->
      <div style="border: 1px solid #eee; border-radius: 8px; overflow: hidden;">
        <!-- 标签页 -->
        <div style="display: flex; border-bottom: 1px solid #eee; background: #fafafa;">
          <el-button
            v-for="tab in imageTabs"
            :key="tab.key"
            type="text"
            :class="{ 'active-tab': activeImageTab === tab.key }"
            @click="activeImageTab = tab.key"
            style="padding: 12px 24px; font-size: 14px;"
          >
            {{ tab.label }}
          </el-button>
        </div>

        <!-- 图片展示区 -->
        <div style="padding: 20px;">
          <div style="display: flex; flex-wrap: wrap; gap: 10px;">
            <!-- 显示前3张图片（点击显式打开大图预览，兼容手机触屏） -->
            <el-image
              v-for="(img, index) in currentTabImages.slice(0, 3)"
              :key="index"
              :src="img.url"
              style="width: 120px; height: 120px; border-radius: 4px; border: 1px solid #eee; cursor: pointer;"
              fit="cover"
              @click="previewImage(index)"
            />

            <!-- 更多图片提示 -->
            <div
              v-if="currentTabImages.length > 3"
              style="width: 120px; height: 120px; border-radius: 4px; border: 1px dashed #ddd; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #999; cursor: pointer;"
              @click="previewAllImages"
            >
              <span style="font-size: 24px;">+</span>
              <span style="font-size: 14px;">{{ currentTabImages.length - 3 }}</span>
            </div>

            <!-- 暂无图片 -->
            <div
              v-if="currentTabImages.length === 0"
              style="width: 100%; text-align: center; padding: 40px; color: #999;"
            >
              暂无图片
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>

  <!-- 图片大图预览（显式打开，兼容手机触屏点击放大；支持保存） -->
  <el-image-viewer
    v-if="previewVisible"
    :url-list="previewUrls"
    :initial-index="previewIndex"
    @close="previewVisible = false"
  >
    <template #toolbar>
      <div class="viewer-save-btn" @click="savePreviewImage" title="保存图片">保存</div>
    </template>
  </el-image-viewer>
</template>

<script setup>
import { formatDate, formatDateTime } from '@/utils/format'
import { imageUrlWithToken, saveImageByUrl } from '@/utils/imageUrl'
import { ref, computed, watch } from 'vue'
import { getOrder, updateOrder } from '@/api/order'
import { getOrderImages } from '@/api/image'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  orderId: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const order = ref({})
const loading = ref(false)
const qrCodeUrl = ref('')
const salesProductImages = ref([])
const factoryProductionImages = ref([])
const shippingDeliveryImages = ref([])

const imageTabs = ref([
  { key: 'sales', label: '销售图片' },
  { key: 'factory', label: '工厂端图片' },
  { key: 'shipping', label: '发货端图片' }
])
const activeImageTab = ref('sales')
const selectedProduceStatus = ref('')

const currentTabImages = computed(() => {
  switch (activeImageTab.value) {
    case 'sales':
      return salesProductImages.value
    case 'factory':
      return factoryProductionImages.value
    case 'shipping':
      return shippingDeliveryImages.value
    default:
      return []
  }
})

function getStatusType(status) {
  return { pending: 'warning', shipped: 'success', virtual: 'info' }[status] || ''
}

function getStatusText(status) {
  return { pending: '待发货', shipped: '已发货', virtual: '虚拟发货' }[status] || status
}

function getProduceStatusType(status) {
  return { unproduce: 'info', producing: 'warning', produced: 'success' }[status] || 'info'
}

function getProduceStatusText(status) {
  return { unproduce: '未生产', producing: '生产中', produced: '生产完成' }[status] || status || '未知'
}


// 预览所有图片（点击 "+N" 打开大图预览，从第一张开始）
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewUrls = computed(() => currentTabImages.value.map(i => i.url))

function previewImage(index) {
  previewIndex.value = index || 0
  previewVisible.value = true
}

function previewAllImages() {
  previewImage(0)
}

// 保存当前预览图片到设备
async function savePreviewImage() {
  const url = previewUrls.value[previewIndex.value]
  if (!url) return
  const ok = await saveImageByUrl(url)
  if (ok) {
    ElMessage.success('已开始保存图片')
  } else {
    ElMessage.info('已在新窗口打开原图，长按图片可保存')
  }
}

// 修改生产进度
async function handleUpdateProduceStatus(newStatus) {
  if (!newStatus || !order.value.order_id) return
  // 如果没变化则忽略
  if (newStatus === order.value.produce_status) return

  try {
    const res = await updateOrder(order.value.order_id, { produce_status: newStatus })
    if (res) {
      const updatedData = res?.data || res || {}
      Object.assign(order.value, updatedData)
      ElMessage.success('生产状态已更新')
      selectedProduceStatus.value = ''
    }
  } catch (error) {
    console.error('更新生产状态失败:', error)
    ElMessage.error(error?.response?.data?.detail || '更新生产状态失败')
    selectedProduceStatus.value = ''
  }
}

async function loadDetail(id) {
  if (!id) return
  loading.value = true
  selectedProduceStatus.value = ''
  try {
    const res = await getOrder(id)
    order.value = res?.data || res || {}

    // 自动生成二维码
    try {
      const qrcodeModule = await import('qrcode')
      const QRCode = qrcodeModule.default || qrcodeModule
      qrCodeUrl.value = await QRCode.toDataURL(id)
    } catch (error) {
      console.error('生成二维码失败:', error)
      qrCodeUrl.value = ''
    }

    // 加载订单图片
    try {
      const result = await getOrderImages(id)
      if (result && result.code === 200 && result.data) {
        salesProductImages.value = result.data
          .filter(item => item.layer === 'sales')
          .map(item => ({ id: item.id, name: `sales_${item.id}`, url: imageUrlWithToken(item.image_url), temp_id: null }))
        factoryProductionImages.value = result.data
          .filter(item => item.layer === 'factory')
          .map(item => ({ id: item.id, name: `factory_${item.id}`, url: imageUrlWithToken(item.image_url), temp_id: null }))
        shippingDeliveryImages.value = result.data
          .filter(item => item.layer === 'shipping')
          .map(item => ({ id: item.id, name: `shipping_${item.id}`, url: imageUrlWithToken(item.image_url), temp_id: null }))
      }
    } catch (error) {
      console.error('加载订单图片失败:', error)
    }
  } catch (error) {
    console.error('加载订单详情失败:', error)
    ElMessage.error('加载订单详情失败')
  } finally {
    loading.value = false
  }
}

// 打开弹窗时加载数据
watch(
  () => props.modelValue,
  (val) => {
    if (val && props.orderId) {
      loadDetail(props.orderId)
    }
  },
  { immediate: true }
)

function handleClosed() {
  order.value = {}
  qrCodeUrl.value = ''
  salesProductImages.value = []
  factoryProductionImages.value = []
  shippingDeliveryImages.value = []
  activeImageTab.value = 'sales'
  selectedProduceStatus.value = ''
}
</script>

<style scoped>
/* 订单详情 - 信息行布局 */
.detail-info-row {
  display: flex;
  align-items: baseline;
  margin-bottom: 14px;
  min-height: 24px;
}
.detail-info-row:last-child { margin-bottom: 0; }
.detail-label {
  width: 88px;
  flex-shrink: 0;
  color: #606266;
  font-size: 14px;
  font-weight: 500;
  text-align: justify;
  text-align-last: justify;
  display: inline-block;
  padding-right: 4px;
}
.detail-label::after {
  content: '：';
  margin-left: 0;
}
.detail-value {
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-all;
}

/* 标签页激活态 */
.active-tab {
  color: #409eff !important;
  font-weight: bold;
  border-bottom: 2px solid #409eff;
}

/* 大图预览"保存"按钮（el-image-viewer toolbar 插槽） */
.viewer-save-btn {
  color: #fff;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 4px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  white-space: nowrap;
}
.viewer-save-btn:active {
  background: rgba(0, 0, 0, 0.55);
}
</style>
