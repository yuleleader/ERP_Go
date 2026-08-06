<template>
  <div class="system-info-container">
    <el-card>
      <template #header>
        <span>系统信息</span>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="系统版本">1.0.0</el-descriptions-item>
        <el-descriptions-item label="数据库类型">SQLite</el-descriptions-item>
        <el-descriptions-item label="Python版本">3.10+</el-descriptions-item>
        <el-descriptions-item label="前端框架">Vue 3</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
// 系统信息展示页（从原系统设置页拆分独立）
</script>

<style scoped>
.system-info-container {
  padding: 20px;
}
</style>
