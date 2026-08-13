<template>
  <div class="dashboard">
    <!-- 订单流程全景：销售 -> 生产 -> 发货 -->
    <OrderFlowPanorama />

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <UniversalOrderList />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import UniversalOrderList from '@/modules/Order/components/UniversalOrderList.vue'
import OrderFlowPanorama from '@/modules/Order/components/OrderFlowPanorama.vue'
</script>

<style scoped>
.dashboard {
  padding: 20px;
}
</style>
