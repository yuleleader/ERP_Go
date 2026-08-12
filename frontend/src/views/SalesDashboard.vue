<template>
  <div class="dashboard">
    <!-- 订单流程全景：替换为原「我的订单」卡片，点击卡片跳订单列表（销售端仅看自己创建的订单） -->
    <OrderFlowPanorama />

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>我创建的订单</span>
          </template>
          <el-table :data="myOrders" style="width: 100%">
            <el-table-column prop="order_id" label="追溯码" width="250" />
            <el-table-column prop="platform_order_no" label="平台订单号" width="150" />
            <el-table-column prop="product_name" label="商品名称" width="150" show-overflow-tooltip />
            <el-table-column prop="sales_amount" label="销售金额" width="100" />
            <el-table-column prop="commission_amount" label="提成" width="100" />
            <el-table-column prop="shipping_status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.shipping_status)">
                  {{ getStatusText(row.shipping_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { getOrders } from '@/api/order'
import { formatDateTime } from '@/utils/format'
import OrderFlowPanorama from '@/modules/Order/components/OrderFlowPanorama.vue'

const userStore = useUserStore()

const myOrders = ref([])

function getStatusType(status) {
  const types = {
    pending: 'warning',
    shipped: 'success',
    virtual: 'info',
    refunded: 'danger'
  }
  return types[status] || ''
}

function getStatusText(status) {
  const texts = {
    pending: '待发货',
    shipped: '已发货',
    virtual: '虚拟发货'
  }
  return texts[status] || status
}

onMounted(async () => {
  try {
    const response = await getOrders({ limit: 15 })
    const orders = response.data || response
    const username = userStore.userInfo?.username
    
    myOrders.value = orders.filter(o => String(o.created_by) === String(username))
  } catch (error) {
    console.error('获取数据失败:', error)
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
  padding: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
  margin-right: 20px;
}

.stat-icon.sales { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-icon.pending { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-icon.amount { background: linear-gradient(135deg, #4facfe, #00f2fe); }
.stat-icon.commission { background: linear-gradient(135deg, #43e97b, #38f9d7); }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}
</style>