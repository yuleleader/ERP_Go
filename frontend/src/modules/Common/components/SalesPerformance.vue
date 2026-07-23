<template>
  <div class="sales-performance">
    <h2>销售人员业绩分析</h2>
    <el-table :data="data" border>
      <el-table-column prop="name" label="销售人员" />
      <el-table-column prop="totalOrders" label="总订单数" />
      <el-table-column prop="shippedOrders" label="已发货" />
      <el-table-column prop="pendingOrders" label="待发货" />
      <el-table-column prop="virtualOrders" label="虚拟发货" />
      <el-table-column prop="annualSales" label="年度营业额" />
    </el-table>
  </div>
</template>

<script setup>
// defineProps, defineEmits are compiler macros, no import needed

defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

defineEmits(['viewDetail'])
</script>

<style scoped>
.sales-performance {
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
</style>