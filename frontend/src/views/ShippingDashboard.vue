<template>
  <div class="dashboard">
    <!-- 订单流程全景：销售 -> 生产 -> 发货 -->
    <OrderFlowPanorama />

    <el-row :gutter="20">
      <el-col :span="8" v-for="card in cards" :key="card.key">
        <el-card class="stat-card clickable" :class="{ active: activeCard === card.key }" @click="filterCard(card.key)">
          <div class="stat-icon" :class="card.key">
            <el-icon><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats[card.field] }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <UniversalOrderList ref="orderListRef" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { getShippingDashboardStats } from '@/api/statistics'
import { Box, Clock, CircleCheck } from '@element-plus/icons-vue'
import UniversalOrderList from '@/modules/Order/components/UniversalOrderList.vue'
import OrderFlowPanorama from '@/modules/Order/components/OrderFlowPanorama.vue'

const orderListRef = ref(null)
const activeCard = ref('all')

const cards = [
  { key: 'all',      icon: Box,         field: 'totalOrders',   label: '所有订单' },
  { key: 'pending',  icon: Clock,       field: 'pendingOrders', label: '待发货订单' },
  { key: 'shipped',  icon: CircleCheck, field: 'shippedOrders', label: '已发货订单' },
]

const stats = reactive({
  totalOrders: 0,
  pendingOrders: 0,
  shippedOrders: 0
})

/**
 * 卡片点击联动筛选
 * all → 清空发货状态筛选
 * pending / shipped → 按发货状态筛选
 */
function filterCard(type) {
  activeCard.value = type

  if (!orderListRef.value) return

  if (type === 'all') {
    orderListRef.value.filterBy('shippingStatus', '')
  } else {
    orderListRef.value.filterBy('shippingStatus', type)
  }
}

onMounted(async () => {
  try {
    const response = await getShippingDashboardStats()
    const data = response.data || response

    stats.totalOrders = data.total_orders || 0
    stats.pendingOrders = data.pending_orders || 0
    stats.shippedOrders = data.shipped_orders || 0
  } catch (error) {
    console.error('获取发货端统计数据失败:', error)
  }
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 18px 16px;
}

.stat-card.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.stat-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.stat-card.clickable.active {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
  background: #ecf5ff;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  margin-right: 16px;
  flex-shrink: 0;
}

.stat-icon.all { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-icon.pending { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-icon.shipped { background: linear-gradient(135deg, #43e97b, #38f9d7); }

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 26px;
  font-weight: bold;
  color: #333;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #999;
  margin-top: 4px;
}
</style>
