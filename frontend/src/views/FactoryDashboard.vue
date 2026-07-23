<template>
  <div class="dashboard">
    <el-row :gutter="12">
      <el-col :span="4" v-for="card in cards" :key="card.key">
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
import { getFactoryDashboardStats } from '@/api/statistics'
import { Box, Clock, CircleCheck, Document } from '@element-plus/icons-vue'
import UniversalOrderList from '@/modules/Order/components/UniversalOrderList.vue'

const orderListRef = ref(null)
const activeCard = ref('all')

const cards = [
  { key: 'all',        icon: Box,          field: 'totalOrders',     label: '全部订单' },
  { key: 'pending',    icon: Clock,         field: 'pendingOrders',   label: '待发货' },
  { key: 'shipped',    icon: CircleCheck,   field: 'shippedOrders',   label: '已发货' },
  { key: 'unproduce',  icon: Document,      field: 'unproduceOrders', label: '未生产' },
  { key: 'producing',  icon: Clock,         field: 'producingOrders', label: '生产中' },
  { key: 'produced',   icon: CircleCheck,   field: 'producedOrders',  label: '生产完成' },
]

const stats = reactive({
  totalOrders: 0,
  pendingOrders: 0,
  shippedOrders: 0,
  unproduceOrders: 0,
  producingOrders: 0,
  producedOrders: 0
})

/**
 * 卡片点击联动筛选
 * all → 清空所有筛选
 * pending/shipped → 按发货状态筛选
 * unproduce/producing/produced → 按生产状态筛选
 */
function filterCard(type) {
  activeCard.value = type

  if (!orderListRef.value) return

  if (type === 'all') {
    orderListRef.value.filterBy('shippingStatus', '')
    orderListRef.value.filterBy('produceStatus', '')
    return
  }

  // 待发货 / 已发货 → 发货状态筛选，清空生产状态
  if (type === 'pending' || type === 'shipped') {
    orderListRef.value.filterBy('produceStatus', '')
    orderListRef.value.filterBy('shippingStatus', type)
    return
  }

  // 未生产 / 生产中 / 生产完成 → 生产状态筛选，清空发货状态
  if (type === 'unproduce' || type === 'producing' || type === 'produced') {
    orderListRef.value.filterBy('shippingStatus', '')
    orderListRef.value.filterBy('produceStatus', type)
    return
  }
}

onMounted(async () => {
  try {
    const response = await getFactoryDashboardStats()
    const data = response.data || response

    stats.totalOrders = data.total_orders || 0
    stats.pendingOrders = data.pending_orders || 0
    stats.shippedOrders = data.shipped_orders || 0
    stats.unproduceOrders = data.unproduce_orders || 0
    stats.producingOrders = data.producing_orders || 0
    stats.producedOrders = data.produced_orders || 0
  } catch (error) {
    console.error('获取工厂端统计数据失败:', error)
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
  padding: 12px 10px;
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
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  margin-right: 10px;
  flex-shrink: 0;
}

.stat-icon.all { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-icon.pending { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-icon.shipped { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.stat-icon.unproduce { background: linear-gradient(135deg, #999999, #cccccc); }
.stat-icon.producing { background: linear-gradient(135deg, #faad14, #ffc53d); }
.stat-icon.produced { background: linear-gradient(135deg, #52c41a, #73d13d); }

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: #999;
  white-space: nowrap;
}
</style>