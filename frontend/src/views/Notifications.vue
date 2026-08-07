<template>
  <div class="notifications-container">
    <el-card class="notification-card">
      <template #header>
        <div class="card-header">
          <span>站内信通知</span>
          <div class="header-actions">
            <el-button type="primary" size="small" @click="handleMarkAllRead" v-if="unreadCount > 0">
              全部已读
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索标题、内容或订单号"
              class="filter-input"
              clearable
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.eventType" placeholder="事件类型" class="filter-input">
              <el-option label="全部" value="" />
              <el-option label="新订单提醒" value="order_created" />
              <el-option label="图片上传完成" value="image_uploaded" />
              <el-option label="订单已发货" value="order_shipped" />
              <el-option label="生产状态变更" value="produce_status_changed" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.isRead" placeholder="阅读状态" class="filter-input">
              <el-option label="全部" :value="''" />
              <el-option label="未读" :value="false" />
              <el-option label="已读" :value="true" />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 通知列表 -->
      <div class="notification-list">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-item"
          :class="{ 'unread': !notification.is_read }"
          @click="handleView(notification)"
        >
          <div class="notification-icon">
            <el-icon v-if="notification.event_type === 'order_created'"><Document /></el-icon>
            <el-icon v-else-if="notification.event_type === 'image_uploaded'"><Picture /></el-icon>
            <el-icon v-else-if="notification.event_type === 'order_shipped'"><Van /></el-icon>
            <el-icon v-else><Bell /></el-icon>
          </div>
          <div class="notification-content">
            <div class="notification-header">
              <span class="notification-title">{{ notification.title }}</span>
              <span class="notification-time">{{ formatDateTime(notification.created_at) }}</span>
            </div>
            <div class="notification-body">
              <p>{{ notification.content }}</p>
            </div>
            <div class="notification-footer">
              <el-button
                v-if="notification.order_id"
                link
                type="primary"
                size="small"
                class="order-id-btn"
                @click.stop="handleViewOrderDetail(notification.order_id)"
              >订单号: {{ notification.order_id }}</el-button>
              <span class="read-status" :class="{ 'read': notification.is_read, 'unread-badge': !notification.is_read }">
                {{ notification.is_read ? '已读' : '未读' }}
              </span>
            </div>
          </div>
          <div class="notification-actions">
            <el-button size="small" @click.stop="handleDelete(notification)">删除</el-button>
          </div>
        </div>

        <div v-if="notifications.length === 0" class="empty-state">
          <el-icon class="empty-icon"><Box /></el-icon>
          <p>暂无通知消息</p>
        </div>
      </div>

      <!-- 分页 -->
      <el-pagination
        v-if="total > 0"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
        layout="total, prev, pager, next, jumper"
        class="pagination"
      />
    </el-card>

    <!-- 通知详情弹窗 -->
    <el-dialog
      v-if="selectedNotification"
      title="通知详情"
      v-model="showDetail"
      width="500px"
      @close="handleCloseDetail"
    >
      <div class="detail-content">
        <div class="detail-header">
          <el-icon v-if="selectedNotification.event_type === 'order_created'" class="detail-icon"><Document /></el-icon>
          <el-icon v-else-if="selectedNotification.event_type === 'image_uploaded'" class="detail-icon"><Picture /></el-icon>
          <el-icon v-else-if="selectedNotification.event_type === 'order_shipped'" class="detail-icon"><Van /></el-icon>
          <el-icon v-else class="detail-icon"><Bell /></el-icon>
          <div class="detail-title">{{ selectedNotification.title }}</div>
        </div>
        <div class="detail-body">
          <p>{{ selectedNotification.content }}</p>
        </div>
        <div class="detail-footer">
          <div class="detail-info">
            <span>订单号: {{ selectedNotification.order_id || '无' }}</span>
            <span>创建时间: {{ formatDateTime(selectedNotification.created_at) }}</span>
            <span>阅读状态: {{ selectedNotification.is_read ? '已读' : '未读' }}</span>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 订单详情弹窗 -->
    <el-dialog v-model="orderDetailVisible" width="950px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <span style="font-size: 16px; font-weight: bold;">订单详情</span>
          <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
            <el-button type="primary" size="small" @click="printOrderDetail">打印</el-button>
            <div class="last-print-time">{{ lastPrintText }}</div>
          </div>
        </div>
      </template>

      <div v-if="orderDetailData">
        <!-- 核心信息区：左右分栏 -->
        <div style="display: flex; gap: 25px; margin-bottom: 25px;">
          <!-- 左侧：基础信息 -->
          <div style="flex: 1; border: 1px solid #eee; border-radius: 8px; padding: 20px;">
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">平台订单号：</span>
              <span style="color: #333; font-weight: 600;">{{ orderDetailData.platform_order_no || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">网店：</span>
              <span style="color: #333;">{{ orderDetailData.shop_id || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">商品名称：</span>
              <span style="color: #333;">{{ orderDetailData.product_name || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">销售金额：</span>
              <span style="color: #333;">{{ orderDetailData.sales_amount || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">下单时间：</span>
              <span style="color: #333;">{{ formatDate(orderDetailData.created_at) }}</span>
            </div>
            <div style="display: flex; align-items: flex-start; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500; flex-shrink: 0;">收货地址：</span>
              <span style="color: #333;">{{ orderDetailData.receiver_address || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">物流公司：</span>
              <span style="color: #333;">{{ orderDetailData.logistics_company || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">运单号1：</span>
              <span style="color: #333;">{{ orderDetailData.logistics_no || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">运单号2：</span>
              <span style="color: #333;">{{ orderDetailData.logistics_no_2 || '——' }}</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
              <span style="width: 100px; color: #666; font-weight: 500;">运费：</span>
              <span style="color: #333;">{{ orderDetailData.freight || '——' }}</span>
            </div>
            <div style="display: flex; align-items: flex-start;">
              <span style="width: 100px; color: #666; font-weight: 500; flex-shrink: 0;">备注：</span>
              <span style="color: #333;">{{ orderDetailData.remark || '——' }}</span>
            </div>
          </div>

          <!-- 右侧：二维码 + 发货状态 + 生产进度 -->
          <div style="width: 180px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px;">
            <div style="border: 1px solid #eee; border-radius: 8px; padding: 15px; text-align: center;">
              <img
                :src="orderQrCodeUrl"
                alt="订单二维码"
                style="width: 130px; height: 130px; margin-bottom: 10px;"
              />
              <div style="padding-top: 10px; border-top: 1px dashed #eee;">
                <span style="font-size: 12px; color: #666;">发货状态：</span>
                <el-tag :type="getStatusType(orderDetailData.shipping_status)" size="small">
                  {{ getStatusText(orderDetailData.shipping_status) }}
                </el-tag>
              </div>
            </div>

            <!-- 生产进度 -->
            <div style="border: 1px solid #eee; border-radius: 8px; padding: 15px;">
              <div style="font-size: 13px; font-weight: 600; margin-bottom: 10px; color: #333;">生产进度</div>
              <div style="margin-bottom: 8px;">
                <el-tag :type="getProduceStatusType(orderDetailData.produce_status)" size="small">
                  {{ getProduceStatusText(orderDetailData.produce_status) }}
                </el-tag>
              </div>
              <div v-if="orderDetailData.produce_status_update_at" style="font-size: 11px; color: #999; margin-bottom: 10px;">
                {{ formatDate(orderDetailData.produce_status_update_at) }}
                <span v-if="orderDetailData.produce_status_update_user"> · {{ orderDetailData.produce_status_update_user }}</span>
              </div>
              <el-select
                v-if="canNotifChangeProduceStatus"
                v-model="notifSelectedProduceStatus"
                placeholder="修改状态"
                size="small"
                style="width: 100%;"
                @change="handleNotifUpdateProduceStatus"
              >
                <el-option label="未生产" value="unproduce" />
                <el-option label="生产中" value="producing" />
                <el-option label="生产完成" value="produced" />
              </el-select>
            </div>
          </div>
        </div>

        <!-- 图片预览区 -->
        <div style="border: 1px solid #eee; border-radius: 8px; overflow: hidden;">
          <div style="display: flex; border-bottom: 1px solid #eee; background: #fafafa;">
            <el-button
              v-for="tab in imageTabs"
              :key="tab.key"
              type="text"
              :class="{ 'active-tab': activeImageTab === tab.key }"
              @click="activeImageTab = tab.key"
              style="padding: 12px 24px; font-size: 14px;"
            >{{ tab.label }}</el-button>
          </div>
          <div style="padding: 20px;">
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
              <el-image
                v-for="(img, index) in orderTabImages.slice(0, 3)"
                :key="index"
                :src="img.url"
                style="width: 120px; height: 120px; border-radius: 4px; border: 1px solid #eee; cursor: pointer;"
                fit="cover"
                @click="previewOrderImage(index)"
              />
              <div
                v-if="orderTabImages.length > 3"
                style="width: 120px; height: 120px; border-radius: 4px; border: 1px dashed #ddd; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #999; cursor: pointer;"
                @click="previewOrderAllImages"
              >
                <span style="font-size: 24px;">+</span>
                <span style="font-size: 14px;">{{ orderTabImages.length - 3 }}</span>
              </div>
              <div v-if="orderTabImages.length === 0" style="width: 100%; text-align: center; padding: 40px; color: #999;">暂无图片</div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>

  <!-- 图片大图预览（显式打开，兼容手机触屏点击放大；支持保存） -->
  <el-image-viewer
    v-if="orderPreviewVisible"
    :url-list="orderPreviewUrls"
    :initial-index="orderPreviewIndex"
    @close="orderPreviewVisible = false"
  >
    <template #toolbar>
      <div class="viewer-save-btn" @click="saveOrderPreviewImage" title="保存图片">保存</div>
    </template>
  </el-image-viewer>
</template>

<script setup>
import { formatDate, formatDateTime } from '@/utils/format'
import { imageUrlWithToken, saveImageByUrl } from '@/utils/imageUrl'
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Picture, Van, Bell, Box, Search, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getNotifications, getUnreadCount, markAsRead, markAllAsRead, deleteNotification } from '@/api/notification'
import { getOrder, updateOrder, markOrderPrinted } from '@/api/order'
import { getOrderImages } from '@/api/image'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()

// 筛选条件
const filters = reactive({
  keyword: '',
  eventType: '',
  isRead: ''
})

// 分页参数
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 数据列表
const notifications = ref([])
const unreadCount = ref(0)

// 详情弹窗
const selectedNotification = ref(null)
const showDetail = ref(false)

// 订单详情弹窗
const orderDetailVisible = ref(false)
const orderDetailData = ref(null)
const orderQrCodeUrl = ref('')
const notifSelectedProduceStatus = ref('')

// 当前站内信订单详情的上次打印时间显示
const lastPrintText = computed(() => {
  const t = orderDetailData.value?.last_print_at
  if (!t) return '未打印'
  try {
    const d = new Date(t)
    const pad = n => String(n).padStart(2, '0')
    return `上次打印时间：${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch (e) {
    return '上次打印时间：' + t
  }
})

// 通知详情弹窗内"修改生产状态"是否可用：已发货/已虚拟发货不可改；销售仅可改自己创建的订单
const canNotifChangeProduceStatus = computed(() => {
  const d = orderDetailData.value
  if (!d) return false
  if (d.shipping_status === 'shipped' || d.shipping_status === 'virtual' || d.shipping_status === 'virtual_shipped') {
    return false
  }
  if (userStore.role === 'sales') {
    return d.created_by === userStore.username
  }
  return ['boss', 'factory', 'shipping'].includes(userStore.role)
})

// 订单图片相关
const orderSalesImages = ref([])
const orderFactoryImages = ref([])
const orderShippingImages = ref([])
const activeImageTab = ref('sales')

const imageTabs = [
  { key: 'sales', label: '销售图片' },
  { key: 'factory', label: '工厂端图片' },
  { key: 'shipping', label: '发货端图片' }
]

const orderTabImages = computed(() => {
  const map = {
    sales: orderSalesImages.value,
    factory: orderFactoryImages.value,
    shipping: orderShippingImages.value
  }
  return map[activeImageTab.value] || []
})

// 格式化时间

// 获取通知列表
async function fetchNotifications() {
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.eventType) params.event_type = filters.eventType
    // 下拉选项值是布尔（true/false），直接传给后端（后端 is_read 为 Optional[bool]）
    if (filters.isRead !== '') params.is_read = filters.isRead

    const response = await getNotifications(params)
    notifications.value = response.items || []
    total.value = response.total || 0
  } catch (error) {
    console.error('获取通知列表失败:', error)
  }
}

// 查询
function handleSearch() {
  currentPage.value = 1
  fetchNotifications()
}

// 重置
function handleReset() {
  filters.keyword = ''
  filters.eventType = ''
  filters.isRead = ''
  currentPage.value = 1
  fetchNotifications()
}

// 分页变更
function handlePageChange(page) {
  currentPage.value = page
  fetchNotifications()
}

// 查看详情
async function handleView(notification) {
  selectedNotification.value = notification
  showDetail.value = true

  // 标记为已读
  if (!notification.is_read) {
    try {
      await markAsRead(notification.id)
      notification.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (error) {
      console.error('标记为已读失败:', error)
    }
  }
}

// 关闭详情
function handleCloseDetail() {
  showDetail.value = false
  selectedNotification.value = null
}

// 标记全部已读
async function handleMarkAllRead() {
  try {
    await markAllAsRead()
    notifications.value.forEach(n => n.is_read = true)
    unreadCount.value = 0
    fetchNotifications()
  } catch (error) {
    console.error('标记全部已读失败:', error)
  }
}

// 删除通知
async function handleDelete(notification) {
  try {
    await deleteNotification(notification.id)
    notifications.value = notifications.value.filter(n => n.id !== notification.id)
    if (!notification.is_read) {
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
    total.value -= 1
  } catch (error) {
    console.error('删除通知失败:', error)
  }
}

// 格式化日期（YYYY-MM-DD）

// 发货状态类型
function getStatusType(status) {
  return { pending: 'warning', shipped: 'success', virtual: 'info' }[status] || ''
}

// 发货状态文本
function getStatusText(status) {
  return { pending: '待发货', shipped: '已发货', virtual: '虚拟发货' }[status] || status
}

// 生产状态类型
function getProduceStatusType(status) {
  return { unproduce: 'info', producing: 'warning', produced: 'success' }[status] || 'info'
}

// 生产状态文本
function getProduceStatusText(status) {
  return { unproduce: '未生产', producing: '生产中', produced: '生产完成' }[status] || status || '未知'
}

// 修改站内信订单详情中的生产状态
async function handleNotifUpdateProduceStatus(newStatus) {
  if (!newStatus || !orderDetailData.value?.order_id) return
  if (newStatus === orderDetailData.value.produce_status) { notifSelectedProduceStatus.value = ''; return }

  try {
    const res = await updateOrder(orderDetailData.value.order_id, { produce_status: newStatus })
    if (res) {
      const updated = res?.data || res || {}
      Object.assign(orderDetailData.value, updated)
      ElMessage.success('生产状态已更新')
    }
  } catch (error) {
    console.error('更新生产状态失败:', error)
    ElMessage.error(error?.response?.data?.detail || '更新失败')
  }
  notifSelectedProduceStatus.value = ''
}

// 查看订单详情
async function handleViewOrderDetail(orderId) {
  try {
    orderDetailData.value = null
    orderDetailVisible.value = true
    notifSelectedProduceStatus.value = ''
    const res = await getOrder(orderId)
    orderDetailData.value = res

    // 生成二维码
    generateOrderQRCode(orderId)

    // 加载订单图片
    const imgResult = await getOrderImages(orderId)
    if (imgResult.code === 200 && imgResult.data) {
      orderSalesImages.value = imgResult.data.filter(item => item.layer === 'sales').map(item => ({
        id: item.id, name: `sales_${item.id}`, url: imageUrlWithToken(item.image_url)
      }))
      orderFactoryImages.value = imgResult.data.filter(item => item.layer === 'factory').map(item => ({
        id: item.id, name: `factory_${item.id}`, url: imageUrlWithToken(item.image_url)
      }))
      orderShippingImages.value = imgResult.data.filter(item => item.layer === 'shipping').map(item => ({
        id: item.id, name: `shipping_${item.id}`, url: imageUrlWithToken(item.image_url)
      }))
    }
  } catch (error) {
    console.error('获取订单详情失败:', error)
    orderDetailVisible.value = false
  }
}

// 生成二维码
async function generateOrderQRCode(orderId) {
  try {
    const QRCode = await import('qrcode')
    const QRCodeModule = QRCode.default || QRCode
    orderQrCodeUrl.value = await QRCodeModule.toDataURL(orderId)
  } catch (error) {
    console.error('生成二维码失败:', error)
    orderQrCodeUrl.value = ''
  }
}

// 预览图片（点击缩略图 / "+N" 均打开大图预览，兼容手机触屏）
const orderPreviewVisible = ref(false)
const orderPreviewIndex = ref(0)
const orderPreviewUrls = computed(() => orderTabImages.value.map(i => i.url))

function previewOrderImage(index) {
  const urls = orderPreviewUrls.value
  if (urls.length === 0) return
  orderPreviewIndex.value = Math.min(index || 0, urls.length - 1)
  orderPreviewVisible.value = true
}

function previewOrderAllImages() {
  previewOrderImage(0)
}

// 保存当前预览图片到设备
async function saveOrderPreviewImage() {
  const url = orderPreviewUrls.value[orderPreviewIndex.value]
  if (!url) return
  const ok = await saveImageByUrl(url)
  if (ok) {
    ElMessage.success('已开始保存图片')
  } else {
    ElMessage.info('已在新窗口打开原图，长按图片可保存')
  }
}

// 获取第一张商品图片URL
function getFirstOrderProductImage() {
  if (orderSalesImages.value.length > 0) return orderSalesImages.value[0].url
  if (orderFactoryImages.value.length > 0) return orderFactoryImages.value[0].url
  if (orderShippingImages.value.length > 0) return orderShippingImages.value[0].url
  return ''
}

// 打印订单详情（先标记打印时间，再开打印窗口）
async function printOrderDetail() {
  if (!orderDetailData.value) return
  const order = orderDetailData.value
  // 标记打印（更新 last_print_at）
  try {
    const updated = await markOrderPrinted(order.order_id || order.orderId)
    const data = updated?.data || updated
    if (data) {
      order.last_print_at = data.last_print_at
    }
  } catch (e) {
    console.warn('标记打印时间失败：', e)
  }

  const firstImg = getFirstOrderProductImage()

  const printContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>商品单据打印</title>
<style>
  /* ===== 基础重置 & A4 页面 ===== */
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "SimSun", "宋体", "STSong", serif;
    font-size: 12pt;
    color: #000;
    background: #f0f0f0;
    line-height: 1.5;
    padding: 10mm;
  }

  .btn-print {
    display: block; margin: 0 auto 8mm; padding: 7mm 16mm;
    border: none; background: #1a56a3; color: #fff;
    font-family: "Microsoft YaHei","SimSun",serif; font-size: 14pt;
    cursor: pointer; border-radius: 2px;
  }
  .btn-print:hover { background: #144684; }

  /* ===== A4 纸张容器 ===== */
  .a4-sheet {
    width: 210mm; min-height: 287mm; max-height: 297mm;
    background: #fff; margin: 0 auto;
    padding: 15mm 18mm;
    overflow: hidden;
    page-break-inside: avoid;
  }

  /* ===== 标题区 ===== */
  .sheet-title {
    text-align: center;
    font-size: 20pt;
    font-weight: bold;
    letter-spacing: 4pt;
    margin-bottom: 8mm;
    padding-bottom: 5mm;
    border-bottom: 2pt solid #222;
  }

  /* ===== 核心信息区（左文右码） ===== */
  .main-section { display: flex; gap: 12mm; margin-bottom: 8mm; }

  .info-body { flex: 1; min-width: 0; }

  /* ---- 信息行：标签 + 值 两端对齐 ---- */
  .info-row {
    display: flex;
    align-items: baseline;
    margin-bottom: 3.5mm;
    line-height: 1.6;
  }
  .info-row:last-child { margin-bottom: 0; }

  .lbl {
    flex-shrink: 0;
    width: 64pt;
    font-weight: bold;
    color: #111;
    white-space: nowrap;          /* 禁止标签内折行 */
    text-align-last: justify;
    text-align: justify;
  }
  .lbl::after { content: '：'; white-space: pre; }

  .val {
    flex: 1; min-width: 0;
    word-break: break-all;
    color: #222;
  }

  /* 核心字段突出 */
  .row-product .val   { font-size: 14pt; font-weight: bold; color: #000; }
  .row-order-no .val  { font-size: 13pt; font-weight: bold; color: #111; letter-spacing: 0.5pt; }
  .row-shop .val      { font-size: 11.5pt; }
  .row-time .val      { font-size: 11.5pt; }
  .row-creator .val   { font-size: 11.5pt; }
  .row-address .val   { font-size: 11pt; line-height: 1.65; }
  .row-remark .val    { font-size: 11pt; }

  /* 二维码区 */
  .qr-zone {
    width: 38mm; height: 38mm; flex-shrink: 0;
    border: 1.5pt solid #bbb; border-radius: 2pt;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden; background: #fafafa;
  }
  .qr-zone img { width: 34mm; height: 34mm; object-fit: contain; }

  /* ===== 分隔线 ===== */
  .divider {
    height: 1pt; background: #ccc; margin: 6mm 0;
  }

  /* ===== 图片区 ===== */
  .img-section-title {
    font-size: 11pt; font-weight: bold; color: #555;
    margin-bottom: 3mm; letter-spacing: 1pt;
  }
  .img-box {
    width: 100%; height: 140mm;
    border: 1pt solid #bbb; border-radius: 2pt;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden; background: #fafafa;
  }
  .img-box img { max-width: 94%; max-height: 136mm; object-fit: contain; }
  .no-img { color: #aaa; font-size: 14pt; }

  /* ===== 打印样式 ===== */
  @media print {
    @page {
      size: A4 portrait;
      margin: 10mm;
    }
    body { background: #fff; padding: 0; }
    .btn-print { display: none !important; }
    .a4-sheet {
      width: 100%; min-height: 100%; max-height: none;
      padding: 13mm 16mm; margin: 0;
    }
    .img-box { height: auto; min-height: 120mm; max-height: 160mm; }
  }
</style>
</head>
<body>

<button class="btn-print" onclick="window.print();var d=new Date(),z=function(n){return(n<10?'0':'')+n},s=d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate())+' '+z(d.getHours())+':'+z(d.getMinutes())+':'+z(d.getSeconds());document.getElementById('printTimeDisplay').textContent='上次打印时间：'+s;">点击打印单据</button>
<div id="printTimeDisplay" style="text-align:center;margin:10px auto 0;color:#666;font-size:14px;font-family:'Microsoft YaHei',sans-serif;"></div>

<div class="a4-sheet">

  <!-- 标题 -->
  <div class="sheet-title">订 货 单 据</div>

  <!-- 主信息区 -->
  <div class="main-section">
    <div class="info-body">

      <!-- 商品名称 — 核心，放大加粗 -->
      <div class="info-row row-product">
        <span class="lbl">商品名称</span>
        <span class="val">${order.product_name || '——'}</span>
      </div>

      <!-- 平台 -->
      <div class="info-row row-shop">
        <span class="lbl">平台</span>
        <span class="val">${order.shop_id || '——'}</span>
      </div>

      <!-- 订单号 — 关键信息，加粗 -->
      <div class="info-row row-order-no">
        <span class="lbl">订单号</span>
        <span class="val">${order.platform_order_no || order.order_id || '——'}</span>
      </div>

      <!-- 下单时间 -->
      <div class="info-row row-time">
        <span class="lbl">下单时间</span>
        <span class="val">${formatDate(order.created_at) || '——'}</span>
      </div>

      <!-- 创建人 -->
      <div class="info-row row-creator">
        <span class="lbl">创建人</span>
        <span class="val">${order.creator_real_name || '——'}</span>
      </div>

      <!-- 收货地址 -->
      <div class="info-row row-address">
        <span class="lbl">收货地址</span>
        <span class="val">${order.receiver_address || '——'}</span>
      </div>

      <!-- 备注 -->
      <div class="info-row row-remark">
        <span class="lbl">备注</span>
        <span class="val">${order.remark || '——'}</span>
      </div>

    </div>

    <!-- 二维码 -->
    <div class="qr-zone">
      ${orderQrCodeUrl.value ? '<img src="' + orderQrCodeUrl.value + '" alt="二维码">' : '<span style="color:#bbb;font-size:9pt;">无二维码</span>'}
    </div>
  </div>

  <!-- 分隔线 -->
  <div class="divider"></div>

  <!-- 商品图片区 -->
  <div class="img-section-title">商品图片</div>
  <div class="img-box">
    ${firstImg ? '<img src="' + firstImg + '" alt="商品图片">' : '<span class="no-img">暂无商品图片</span>'}
  </div>

</div><!-- /a4-sheet -->

</body>
</html>`

  const printWindow = window.open('', '_blank', 'width=900,height=700')
  if (!printWindow) {
    ElMessage.error('打印窗口被拦截，请允许弹出窗口后重试')
    return
  }
  printWindow.document.write(printContent)
  printWindow.document.close()
}

onMounted(() => {
  fetchNotifications()
  // 加载未读数量（"全部已读"按钮依赖此数 > 0 才显示）
  getUnreadCount()
    .then(res => { unreadCount.value = res.unread_count || 0 })
    .catch(() => { unreadCount.value = 0 })
})
</script>

<style scoped>
.notifications-container {
  padding: 20px;
}

.notification-card {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-section {
  padding: 15px 0;
  border-bottom: 1px solid #eee;
}

.filter-input {
  width: 100%;
}

.notification-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  padding: 15px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.2s;
}

.notification-item:hover {
  background-color: #fafafa;
}

.notification-item.unread {
  background-color: #fff3e6;
}

.notification-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  flex-shrink: 0;
  margin-right: 15px;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.notification-title {
  font-weight: 600;
  color: #333;
}

.notification-time {
  font-size: 12px;
  color: #999;
}

.notification-body {
  margin-bottom: 8px;
}

.notification-body p {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-id {
  font-size: 12px;
  color: #666;
}

.order-id-btn {
  font-size: 12px;
  padding: 0;
  height: auto;
}

/* 订单详情弹窗样式 - active tab */
:deep(.active-tab) {
  color: #409EFF;
  border-bottom: 2px solid #409EFF;
  border-radius: 0;
}


.read-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.read-status.read {
  background-color: #e8f5e9;
  color: #4caf50;
}

.read-status.unread-badge {
  background-color: #ffeb3b;
  color: #f9a825;
}

.notification-actions {
  margin-left: 15px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 15px;
  color: #ddd;
}

.pagination {
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.detail-content {
  padding: 10px;
}

.detail-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.detail-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  margin-right: 15px;
}

.detail-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.detail-body {
  margin-bottom: 20px;
}

.detail-body p {
  color: #666;
  line-height: 1.8;
  margin: 0;
}

.detail-footer {
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.detail-info {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: 14px;
  color: #666;
}

/* 站内信订单详情"打印"按钮下方的上次打印时间显示 */
.last-print-time {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  white-space: nowrap;
  user-select: none;
  -webkit-user-select: none;
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