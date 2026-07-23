<template>
  <div class="order-overview">
    <h2>订单总览</h2>
    <div class="stats">
      <div class="stat-item">
        <span class="label">总订单数</span>
        <span class="value">{{ data.totalOrders }}</span>
        <span class="trend" :class="data.totalOrdersTrend >= 0 ? 'up' : 'down'">
          {{ data.totalOrdersTrend >= 0 ? '+' : '' }}{{ data.totalOrdersTrend }}%
        </span>
      </div>
      <div class="stat-item">
        <span class="label">已发货</span>
        <span class="value">{{ data.shippedOrders }}</span>
        <span class="percent">{{ data.shippedPercentage }}%</span>
      </div>
      <div class="stat-item" :class="{ warning: data.pendingWarning }">
        <span class="label">待发货</span>
        <span class="value">{{ data.pendingOrders }}</span>
        <span v-if="data.pendingWarning" class="warning-text">预警</span>
      </div>
      <div class="stat-item">
        <span class="label">虚拟发货</span>
        <span class="value">{{ data.virtualOrders }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// defineProps, defineEmits are compiler macros, no import needed

const props = defineProps({
  data: {
    type: Object,
    default: () => ({
      totalOrders: 0,
      shippedOrders: 0,
      pendingOrders: 0,
      virtualOrders: 0,
      totalOrdersTrend: 0,
      shippedPercentage: 0,
      pendingWarning: false
    })
  }
})

const emit = defineEmits(['drill-down'])

function drillDown(type) {
  emit('drill-down', type)
}
</script>

<style scoped>
.order-overview {
  background: #1a2332;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #334155;
}

h2 {
  color: #60a5fa;
  font-size: 20px;
  margin-bottom: 16px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-item {
  background: rgba(30, 41, 59, 0.8);
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  
  &.warning {
    border: 1px solid #f59e0b;
    background: rgba(245, 158, 11, 0.1);
  }
}

.label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #f8fafc;
}

.trend {
  font-size: 12px;
  
  &.up { color: #10b981; }
  &.down { color: #ef4444; }
}

.percent {
  font-size: 12px;
  color: #10b981;
}

.warning-text {
  font-size: 12px;
  color: #f59e0b;
}
</style>