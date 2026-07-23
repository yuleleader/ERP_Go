<template>
  <div class="finance-statistics">
    <h2>财务数据统计</h2>
    <div class="stats-row">
      <div class="stat-card">
        <span class="label">年度营业额</span>
        <span class="value">¥{{ data.annualSales.toLocaleString() }}</span>
        <span class="growth" :class="data.annualGrowth >= 0 ? 'up' : 'down'">
          {{ data.annualGrowth >= 0 ? '+' : '' }}{{ data.annualGrowth }}%
        </span>
      </div>
      <div class="stat-card">
        <span class="label">月度营业额</span>
        <span class="value">¥{{ data.monthlySales.toLocaleString() }}</span>
        <span class="growth" :class="data.monthlyGrowth >= 0 ? 'up' : 'down'">
          {{ data.monthlyGrowth >= 0 ? '+' : '' }}{{ data.monthlyGrowth }}%
        </span>
      </div>
    </div>
    <div class="chart-section">
      <h3>趋势图</h3>
      <div class="chart">
        <div 
          v-for="(item, index) in data.trendData" 
          :key="index"
          class="bar"
          :style="{ height: (item.value / maxValue * 100) + '%' }"
        >
          <span class="bar-label">{{ item.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    default: () => ({
      annualSales: 0,
      monthlySales: 0,
      annualGrowth: 0,
      monthlyGrowth: 0,
      trendData: []
    })
  }
})

const maxValue = computed(() => {
  if (!props.data.trendData || props.data.trendData.length === 0) return 100
  return Math.max(...props.data.trendData.map(d => d.value ?? 0))
})
</script>

<style scoped>
.finance-statistics {
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

h3 {
  color: #94a3b8;
  font-size: 14px;
  margin-bottom: 12px;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  background: rgba(30, 41, 59, 0.8);
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #f8fafc;
}

.growth {
  font-size: 12px;
  
  &.up { color: #10b981; }
  &.down { color: #ef4444; }
}

.chart {
  display: flex;
  align-items: flex-end;
  height: 150px;
  gap: 8px;
}

.bar {
  flex: 1;
  background: linear-gradient(180deg, #3b82f6, #1d4ed8);
  border-radius: 4px 4px 0 0;
  position: relative;
  min-height: 10px;
}

.bar-label {
  position: absolute;
  bottom: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
}
</style>