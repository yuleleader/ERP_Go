<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon sales">
            <el-icon><ShoppingCart /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.myOrders }}</div>
            <div class="stat-label">我的订单</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon pending">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.pendingOrders }}</div>
            <div class="stat-label">待发货</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon amount">
            <el-icon><Money /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">¥{{ stats.mySales }}</div>
            <div class="stat-label">我的销售额</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon commission">
            <el-icon><Wallet /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">¥{{ stats.myCommission }}</div>
            <div class="stat-label">我的提成</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

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
            <el-table-column prop="created_at" label="创建时间" width="120" :formatter="(row) => formatDate(row.created_at)" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { getOrders } from '@/api/order'
import { getTheoreticalCommission, getTotalSales } from '@/api/statistics'
import { formatDate } from '@/utils/format'
import { ShoppingCart, Clock, Money, Wallet } from '@element-plus/icons-vue'

const userStore = useUserStore()

const stats = reactive({
  myOrders: 0,
  pendingOrders: 0,
  mySales: 0,
  myCommission: 0
})

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
    virtual: '虚拟发货',
    refunded: '已退货/退款'
  }
  return texts[status] || status
}

onMounted(async () => {
  try {
    // 我的提成/销售额：直接调用后端统计接口（按当前销售账号自动过滤，避免前端仅累加前 N 条导致失真）
    const [commissionRes, salesRes, ordersRes] = await Promise.all([
      getTheoreticalCommission(),
      getTotalSales(),
      getOrders({ limit: 100 })
    ])
    const commissionData = commissionRes.data || commissionRes
    const salesData = salesRes.data || salesRes
    const orders = (ordersRes.data || ordersRes) || []
    const username = userStore.userInfo?.username

    myOrders.value = orders.filter(o => String(o.created_by) === String(username))

    stats.myOrders = myOrders.value.length
    stats.pendingOrders = myOrders.value.filter(o => o.shipping_status === 'pending').length
    stats.mySales = Number(salesData.total_amount || 0)
    stats.myCommission = Number(commissionData.total_commission || 0)
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