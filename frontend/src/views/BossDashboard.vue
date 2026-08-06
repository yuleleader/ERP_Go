<template>
  <div class="dashboard">
    <!-- 经营概览（压缩为金额类一行） -->
    <div class="section-title">经营概览</div>
    <el-row :gutter="20">
      <el-col :span="12">
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
      <el-col :span="12">
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

    <!-- 订单流程全景：销售 -> 生产 -> 发货 -->
    <div class="section-title">订单流程全景</div>
    <div class="flow">
      <!-- 销售 -->
      <div class="flow-stage">
        <div class="flow-stage-title sales">销售</div>
        <div class="flow-metrics">
          <div class="flow-metric" @click="goOrders()">
            <div class="fm-value">{{ flow.sales.totalOrders }}</div>
            <div class="fm-label">总订单数</div>
          </div>
          <div class="flow-metric" @click="goOrders({ shipping_status: 'pending' })">
            <div class="fm-value warn">{{ flow.sales.pendingOrders }}</div>
            <div class="fm-label">未发货</div>
          </div>
          <div class="flow-metric" @click="goOrders({ shipping_status: 'virtual' })">
            <div class="fm-value info">{{ flow.sales.virtualOrders }}</div>
            <div class="fm-label">虚拟发货</div>
          </div>
          <div class="flow-metric" @click="goOrders({ shipping_status: 'refunded' })">
            <div class="fm-value danger">{{ flow.sales.refundedOrders }}</div>
            <div class="fm-label">已退货</div>
          </div>
        </div>
      </div>

      <div class="flow-arrow"><el-icon><Right /></el-icon></div>

      <!-- 生产 -->
      <div class="flow-stage">
        <div class="flow-stage-title produce">生产</div>
        <div class="flow-metrics">
          <div class="flow-metric" @click="goOrders({ produce_status: 'unproduce' })">
            <div class="fm-value info">{{ flow.produce.unproduceOrders }}</div>
            <div class="fm-label">未生产</div>
          </div>
          <div class="flow-metric" @click="goOrders({ produce_status: 'producing' })">
            <div class="fm-value warn">{{ flow.produce.producingOrders }}</div>
            <div class="fm-label">生产中</div>
          </div>
          <div class="flow-metric" @click="goOrders({ produce_status: 'produced' })">
            <div class="fm-value success">{{ flow.produce.producedOrders }}</div>
            <div class="fm-label">生产完成</div>
          </div>
        </div>
      </div>

      <div class="flow-arrow"><el-icon><Right /></el-icon></div>

      <!-- 发货 -->
      <div class="flow-stage">
        <div class="flow-stage-title shipping">发货</div>
        <div class="flow-metrics">
          <div class="flow-metric" @click="goOrders({ shipping_status: 'pending' })">
            <div class="fm-value warn">{{ flow.shipping.pendingOrders }}</div>
            <div class="fm-label">未发货</div>
          </div>
          <div class="flow-metric" @click="goOrders({ shipping_status: 'shipped' })">
            <div class="fm-value success">{{ flow.shipping.shippedOrders }}</div>
            <div class="fm-label">已发货</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { getOverviewStatistics, getCommissionByUser, getProcessFlow } from '@/api/statistics'
import { Money, Wallet, Right } from '@element-plus/icons-vue'

const stats = reactive({
  totalSales: 0,
  totalCommission: 0
})

const flow = reactive({
  sales: { totalOrders: 0, pendingOrders: 0, virtualOrders: 0, refundedOrders: 0 },
  produce: { unproduceOrders: 0, producingOrders: 0, producedOrders: 0 },
  shipping: { pendingOrders: 0, shippedOrders: 0 }
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
    const [overviewRes, commissionRes, flowRes] = await Promise.all([
      getOverviewStatistics(),
      getCommissionByUser(),
      getProcessFlow()
    ])

    const overview = overviewRes || {}
    stats.totalSales = parseFloat((overview.total_sales || 0).toFixed(2)).toLocaleString('zh-CN')

    const commissionSummary = (commissionRes && commissionRes.summary) || {}
    stats.totalCommission = parseFloat((commissionSummary.total_commission || 0).toFixed(2)).toLocaleString('zh-CN')

    const f = (flowRes && flowRes.data) || flowRes || {}
    if (f.sales) {
      flow.sales.totalOrders = f.sales.total_orders || 0
      flow.sales.pendingOrders = f.sales.pending_orders || 0
      flow.sales.virtualOrders = f.sales.virtual_orders || 0
      flow.sales.refundedOrders = f.sales.refunded_orders || 0
    }
    if (f.produce) {
      flow.produce.unproduceOrders = f.produce.unproduce_orders || 0
      flow.produce.producingOrders = f.produce.producing_orders || 0
      flow.produce.producedOrders = f.produce.produced_orders || 0
    }
    if (f.shipping) {
      flow.shipping.pendingOrders = f.shipping.pending_orders || 0
      flow.shipping.shippedOrders = f.shipping.shipped_orders || 0
    }
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

/* ===== 订单流程全景 ===== */
.flow {
  display: flex;
  align-items: stretch;
  gap: 0;
  flex-wrap: wrap;
}

.flow-stage {
  flex: 1 1 0;
  min-width: 200px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.flow-stage-title {
  font-size: 15px;
  font-weight: 700;
  text-align: center;
  padding: 8px 0;
  border-radius: 8px;
  margin-bottom: 14px;
  color: #fff;
}

.flow-stage-title.sales { background: linear-gradient(135deg, #667eea, #764ba2); }
.flow-stage-title.produce { background: linear-gradient(135deg, #faad14, #ffc53d); }
.flow-stage-title.shipping { background: linear-gradient(135deg, #43e97b, #38f9d7); }

.flow-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.flow-metric {
  background: #f7f8fa;
  border-radius: 8px;
  padding: 12px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.flow-metric:hover {
  background: #eef5ff;
  border-color: #c6e2ff;
  transform: translateY(-1px);
}

.fm-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.fm-value.warn { color: #e6a23c; }
.fm-value.info { color: #909399; }
.fm-value.danger { color: #f56c6c; }
.fm-value.success { color: #67c23a; }

.fm-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.flow-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  color: #c0c4cc;
  font-size: 26px;
}

@media (max-width: 900px) {
  .flow-arrow {
    width: 100%;
    padding: 6px 0;
    transform: rotate(90deg);
  }
}
</style>
