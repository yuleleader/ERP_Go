<template>
  <div class="sales-ranking">
    <h2>销售排行榜</h2>
    <div class="ranking-list">
      <div 
        v-for="(item, index) in data.slice(0, 10)" 
        :key="item.id"
        class="ranking-item"
      >
        <span class="rank">{{ index + 1 }}</span>
        <div class="bar-container">
          <div 
            class="bar" 
            :style="{ width: (item.salesAmount / maxSales * 100) + '%' }"
          ></div>
        </div>
        <span class="name">{{ item.name }}</span>
        <span class="amount">¥{{ item.salesAmount.toLocaleString() }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

const maxSales = computed(() => {
  if (props.data.length === 0) return 1
  return Math.max(...props.data.map(item => item.salesAmount ?? 0))
})
</script>

<style scoped>
.sales-ranking {
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

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ranking-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rank {
  width: 24px;
  text-align: center;
  font-weight: 700;
  color: #94a3b8;
}

.bar-container {
  flex: 1;
  height: 24px;
  background: rgba(30, 41, 59, 0.8);
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.name {
  width: 60px;
  color: #f8fafc;
  font-size: 14px;
}

.amount {
  width: 100px;
  text-align: right;
  color: #f8fafc;
  font-weight: 600;
}
</style>