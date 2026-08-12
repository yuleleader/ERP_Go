<template>
  <div class="dashboard">
    <!-- 经营概览（三个卡片同一行） -->
    <div class="section-title">经营概览</div>
    <el-row :gutter="20">
      <el-col :span="8">
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
      <el-col :span="8">
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
      <el-col :span="8">
        <el-card class="stat-card clickable compact overdue-card" @click="goOrders({ overdue: true })">
          <div class="stat-icon overdue">
            <el-icon><AlarmClock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value danger">{{ stats.overdueOrders }}</div>
            <div class="stat-label">超期订单（超过 {{ stats.overdueDays }} 天未发货）</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 订单流程全景：销售 -> 生产 -> 发货（共享组件，所有角色工作台通用） -->
    <OrderFlowPanorama />
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { getOverviewStatistics, getCommissionByUser, getOverdueOrders } from '@/api/statistics'
import { Money, Wallet, AlarmClock } from '@element-plus/icons-vue'
import OrderFlowPanorama from '@/modules/Order/components/OrderFlowPanorama.vue'

const stats = reactive({
  totalSales: 0,
  totalCommission: 0,
  overdueOrders: 0,
  overdueDays: 7
})

const router = useRouter()
const userStore = useUserStore()

function goOrders(query = {}) {
  router.push({ path: '/orders', query })
}

function goTo(path) {
  router.push(path)
}

onMounted(async () => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
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
    // 各接口独立容错：单个接口失败不影响其他卡片的数据展示
    const [overviewRes, commissionRes, overdueRes] = await Promise.allSettled([
      getOverviewStatistics(),
      getCommissionByUser(),
      getOverdueOrders()
    ])

    const overview = (overviewRes.status === 'fulfilled' && overviewRes.value) || {}
    stats.totalSales = parseFloat((overview.total_sales || 0).toFixed(2)).toLocaleString('zh-CN')

    const commissionSummary =
      (commissionRes.status === 'fulfilled' && commissionRes.value && commissionRes.value.summary) || {}
    stats.totalCommission = parseFloat((commissionSummary.total_commission || 0).toFixed(2)).toLocaleString('zh-CN')

    const o = (overdueRes.status === 'fulfilled' && overdueRes.value) || {}
    stats.overdueOrders = o.total_overdue || 0
    stats.overdueDays = o.overdue_days || 7

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

.stat-icon.amount { background: linear-gradient(135deg, #4facfe, #00f2fe); }
.stat-icon.commission { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.stat-icon.overdue { background: linear-gradient(135deg, #ff9a9e, #fad0c4); }

.stat-value.danger { color: #f56c6c; }

.overdue-card {
  border: 1px solid #fde2e2;
}

.overdue-tip {
  font-size: 12px;
  color: #c45656;
  flex-shrink: 0;
  margin-left: 12px;
}

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

/* 订单流程全景样式已抽离至 OrderFlowPanorama.vue 组件 */
</style>
