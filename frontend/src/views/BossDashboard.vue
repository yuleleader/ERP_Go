<template>
  <div class="dashboard">
    <!-- 经营概览卡片 -->
    <div class="section-title">经营概览</div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card clickable compact" @click="goOrders()">
          <div class="stat-icon sales">
            <el-icon><Goods /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.totalOrders }}</div>
            <div class="stat-label">总订单数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card clickable compact" @click="goOrders({ shipping_status: 'pending' })">
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
        <el-card class="stat-card clickable compact" @click="goTo('/statistics')">
          <div class="stat-icon amount">
            <el-icon><Money /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">¥{{ stats.totalSales }}</div>
            <div class="stat-label">总销售额</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card clickable compact" @click="goTo('/salary-settlement')">
          <div class="stat-icon commission">
            <el-icon><Wallet /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">¥{{ stats.totalCommission }}</div>
            <div class="stat-label">总提成</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 生产/发货概览卡片（工厂端指标） -->
    <div class="section-title">生产 / 发货概览</div>
    <el-row :gutter="12">
      <el-col :span="4" v-for="card in factoryCards" :key="card.key">
        <el-card class="stat-card clickable compact" @click="goOrders(card.query)">
          <div class="stat-icon" :class="card.key">
            <el-icon><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ factoryStats[card.field] }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="14">
        <el-card>
          <template #header>
            <span>最近订单</span>
          </template>
          <el-table :data="recentOrders" style="width: 100%">
            <el-table-column label="二维码" width="80">
              <template #default="{ row }">
                <el-icon class="qr-icon" color="#4ade80"><Ticket /></el-icon>
              </template>
            </el-table-column>
            <el-table-column prop="creator_real_name" label="订单归属人" width="120">
              <template #default="{ row }">
                {{ row.creator_real_name || (row.created_by ? `销售${row.created_by}` : '未知') }}
              </template>
            </el-table-column>
            <el-table-column prop="platform_order_no" label="平台订单号" width="150" />
            <el-table-column prop="product_name" label="商品名称" width="150" show-overflow-tooltip />
            <el-table-column prop="sales_amount" label="销售金额" width="100">
              <template #default="{ row }">¥{{ row.sales_amount }}</template>
            </el-table-column>
            <el-table-column prop="shipping_status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.shipping_status)">
                  {{ getStatusText(row.shipping_status) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>
            <span>销售排行</span>
          </template>
          <el-table :data="salesRanking" style="width: 100%">
            <el-table-column label="排名" width="60">
              <template #default="{ $index }">
                <el-tag v-if="$index < 3" :type="['success', 'warning', 'info'][$index]">
                  {{ $index + 1 }}
                </el-tag>
                <span v-else>{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="username" label="销售员" />
            <el-table-column prop="orderCount" label="订单数" width="80" />
            <el-table-column prop="totalSales" label="销售额" width="100">
              <template #default="{ row }">¥{{ row.totalSales }}</template>
            </el-table-column>
            <el-table-column prop="commission" label="提成" width="80">
              <template #default="{ row }">¥{{ row.commission }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { getOrders } from '@/api/order'
import { getOverviewStatistics, getDashboardSalesRanking, getFactoryDashboardStats, getCommissionByUser } from '@/api/statistics'
import { Goods, Clock, Money, Wallet, Ticket, Box, CircleCheck, Document, Van } from '@element-plus/icons-vue'

const stats = reactive({
  totalOrders: 0,
  pendingOrders: 0,
  totalSales: 0,
  totalCommission: 0
})

// 工厂端（生产/发货）指标
const factoryStats = reactive({
  shippedOrders: 0,
  unproduceOrders: 0,
  producingOrders: 0,
  producedOrders: 0
})

// 工厂端卡片配置（点击跳转至订单管理并预置筛选）
const factoryCards = [
  { key: 'shipped',   icon: Van,         field: 'shippedOrders',   label: '已发货', query: { shipping_status: 'shipped' } },
  { key: 'unproduce', icon: Document,    field: 'unproduceOrders', label: '未生产', query: { produce_status: 'unproduce' } },
  { key: 'producing', icon: Clock,       field: 'producingOrders', label: '生产中', query: { produce_status: 'producing' } },
  { key: 'produced',  icon: CircleCheck, field: 'producedOrders',  label: '生产完成', query: { produce_status: 'produced' } }
]

const recentOrders = ref([])
const salesRanking = ref([])

function getStatusType(status) {
  const types = {
    pending: 'warning',
    shipped: 'success',
    virtual: 'info'
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

const router = useRouter()
const userStore = useUserStore()

// 跳转到订单管理页并预置筛选条件
function goOrders(query = {}) {
  router.push({ path: '/orders', query })
}

// 通用跳转
function goTo(path) {
  router.push(path)
}

onMounted(async () => {
  // 检查登录状态，如果未登录则跳转到登录页
  if (!userStore.token) {
    router.push('/login')
    return
  }
  
  // 如果用户信息未加载，尝试加载
  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch (e) {
      console.error('获取用户信息失败:', e)
      router.push('/login')
      return
    }
  }
  
  try {
      // 使用后端统计接口，避免拉取全量订单到前端
      const [overviewRes, salesRankingRes, factoryRes, commissionRes] = await Promise.all([
        getOverviewStatistics(),
        getDashboardSalesRanking(5),
        getFactoryDashboardStats(),
        getCommissionByUser()
      ])
      
      const overview = overviewRes || {}
      stats.totalOrders = overview.total_orders || 0
      stats.pendingOrders = overview.pending_orders || 0
      stats.totalSales = parseFloat((overview.total_sales || 0).toFixed(2)).toLocaleString('zh-CN')

      // 总提成（后端聚合的实际提成汇总）
      const commissionSummary = (commissionRes && commissionRes.summary) || {}
      stats.totalCommission = parseFloat((commissionSummary.total_commission || 0).toFixed(2)).toLocaleString('zh-CN')

      // 工厂端（生产/发货）指标
      const factory = factoryRes.data || factoryRes || {}
      factoryStats.shippedOrders = factory.shipped_orders || 0
      factoryStats.unproduceOrders = factory.unproduce_orders || 0
      factoryStats.producingOrders = factory.producing_orders || 0
      factoryStats.producedOrders = factory.produced_orders || 0

      // 销售排行直接使用后端聚合结果
      salesRanking.value = (salesRankingRes.data || salesRankingRes || []).map(item => ({
        username: item.real_name || item.username,
        orderCount: item.order_count || 0,
        totalSales: parseFloat((item.total_sales || 0).toFixed(2)),
        commission: parseFloat((item.total_commission || 0).toFixed(2))
      }))

    // 仅获取最近10条订单用于表格展示
    const ordersRes = await getOrders({ limit: 10 })
    const ordersData = ordersRes.data || ordersRes
    recentOrders.value = Array.isArray(ordersData) ? ordersData : []
  } catch (error) {
    console.error('获取数据失败:', error)
  }
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 4px 0 14px;
  padding-left: 10px;
  border-left: 4px solid #409EFF;
  line-height: 1.2;
}

.section-title:not(:first-child) {
  margin-top: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-card.compact {
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
  border-color: #c6e2ff;
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
  flex-shrink: 0;
}

.stat-card.compact .stat-icon {
  width: 38px;
  height: 38px;
  font-size: 18px;
  border-radius: 8px;
  margin-right: 10px;
}

.stat-icon.sales { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-icon.pending { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-icon.amount { background: linear-gradient(135deg, #4facfe, #00f2fe); }
.stat-icon.commission { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.stat-icon.shipped { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.stat-icon.unproduce { background: linear-gradient(135deg, #999999, #cccccc); }
.stat-icon.producing { background: linear-gradient(135deg, #faad14, #ffc53d); }
.stat-icon.produced { background: linear-gradient(135deg, #52c41a, #73d13d); }

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-card.compact .stat-value {
  font-size: 20px;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}

.stat-card.compact .stat-label {
  font-size: 11px;
  margin-top: 2px;
  white-space: nowrap;
}

.qr-icon {
  font-size: 20px;
  cursor: pointer;
}
</style>