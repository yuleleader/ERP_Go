<template>
  <div class="product-ranking">
    <h2>热销商品分析</h2>
    <div class="product-list">
      <div 
        v-for="(product, index) in data.slice(0, 10)" 
        :key="product.id"
        class="product-item"
      >
        <span class="rank">{{ index + 1 }}</span>
        <span class="name">{{ product.name }}</span>
        <span class="sales">销量: {{ product.sales }}</span>
        <span class="revenue">¥{{ product.revenue.toLocaleString() }}</span>
        <span class="profit" :class="getProfitClass(product.profit)">
          {{ product.profit }}%
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
// defineProps is a compiler macro, no import needed

defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

function getProfitClass(profit) {
  if (profit >= 30) return 'high'
  if (profit >= 20) return 'medium'
  return 'low'
}
</script>

<style scoped>
.product-ranking {
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

.product-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.product-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  background: rgba(30, 41, 59, 0.6);
  border-radius: 6px;
}

.rank {
  width: 24px;
  font-weight: 700;
  color: #94a3b8;
}

.name {
  flex: 1;
  color: #f8fafc;
  font-size: 13px;
}

.sales {
  width: 80px;
  color: #94a3b8;
  font-size: 12px;
}

.revenue {
  width: 100px;
  text-align: right;
  color: #f8fafc;
  font-weight: 600;
}

.profit {
  width: 60px;
  text-align: right;
  font-weight: 600;
  
  &.high { color: #10b981; }
  &.medium { color: #f59e0b; }
  &.low { color: #ef4444; }
}
</style>