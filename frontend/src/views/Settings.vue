<template>
  <div class="settings-container">
    <el-card class="mb-4">
      <template #header>
        <span>参数设置</span>
      </template>

      <el-form :model="settings" label-width="150px">
        <el-form-item label="默认提成比例">
          <el-input-number v-model="settings.defaultCommissionRate" :min="1" :max="100" />
          <span style="margin-left: 10px;">%</span>
        </el-form-item>

        <el-form-item label="临时图片保留时间">
          <el-input-number v-model="settings.tempImageRetentionHours" :min="1" :max="168" />
          <span style="margin-left: 10px;">小时</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
          <el-button @click="resetSettings">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const settings = reactive({
  defaultCommissionRate: 10,
  tempImageRetentionHours: 24
})

function saveSettings() {
  localStorage.setItem('systemSettings', JSON.stringify(settings))
  ElMessage.success('设置保存成功')
}

function resetSettings() {
  settings.defaultCommissionRate = 10
  settings.tempImageRetentionHours = 24
}

const savedSettings = localStorage.getItem('systemSettings')
if (savedSettings) {
  Object.assign(settings, JSON.parse(savedSettings))
}
</script>

<style scoped>
.settings-container {
  padding: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
