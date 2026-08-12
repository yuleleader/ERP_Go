<template>
  <div class="order-flow-panorama">
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
import { getProcessFlow } from '@/api/statistics'
import { Right } from '@element-plus/icons-vue'

const flow = reactive({
  sales: { totalOrders: 0, pendingOrders: 0, virtualOrders: 0, refundedOrders: 0 },
  produce: { unproduceOrders: 0, producingOrders: 0, producedOrders: 0 },
  shipping: { pendingOrders: 0, shippedOrders: 0 }
})

const router = useRouter()

function goOrders(query = {}) {
  router.push({ path: '/orders', query })
}

onMounted(async () => {
  try {
    const res = await getProcessFlow()
    const f = (res && res.data) || res || {}
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
    console.error('获取订单流程全景失败:', error)
  }
})
</script>

<style scoped>
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 4px 0 14px;
  padding-left: 10px;
  border-left: 4px solid #409EFF;
  line-height: 1.2;
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
