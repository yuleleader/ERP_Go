<template>
  <div class="settings-container">
    <el-card class="mb-4">
      <template #header>
        <span>参数设置</span>
      </template>

      <el-form :model="settings" label-width="150px" v-loading="loading">
        <el-form-item label="默认提成比例">
          <el-input-number v-model="settings.defaultCommissionRate" :min="1" :max="100" />
          <span style="margin-left: 10px;">%</span>
        </el-form-item>

        <el-form-item label="临时图片保留时间">
          <el-input-number v-model="settings.tempImageRetentionHours" :min="1" :max="168" />
          <span style="margin-left: 10px;">小时</span>
        </el-form-item>

        <el-form-item label="超期订单天数">
          <el-input-number v-model="settings.overdueOrderDays" :min="1" :max="365" />
          <span style="margin-left: 10px;">天</span>
          <div class="form-hint">下单后超过该天数且尚未发货完成的订单，在工作台经营概览中计为「超期订单」</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveSettings" :loading="saving">保存设置</el-button>
          <el-button @click="resetSettings">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
defineOptions({ name: 'Settings' })
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSettings } from '@/api/setting'

const loading = ref(false)
const saving = ref(false)

const settings = reactive({
  defaultCommissionRate: 10,
  tempImageRetentionHours: 24,
  overdueOrderDays: 7
})

// 从后端加载参数
async function fetchSettings() {
  loading.value = true
  try {
    const res = await getSettings()
    settings.defaultCommissionRate = Number(res.default_commission_rate ?? 10)
    settings.tempImageRetentionHours = Number(res.temp_image_retention_hours ?? 24)
    settings.overdueOrderDays = Number(res.overdue_order_days ?? 7)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取系统参数失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await updateSettings([
      { key: 'default_commission_rate', value: String(settings.defaultCommissionRate), description: '默认提成比例(%)' },
      { key: 'temp_image_retention_hours', value: String(settings.tempImageRetentionHours), description: '临时图片保留时间(小时)' },
      { key: 'overdue_order_days', value: String(settings.overdueOrderDays), description: '超期订单天数' }
    ])
    ElMessage.success('设置保存成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存设置失败')
  } finally {
    saving.value = false
  }
}

function resetSettings() {
  settings.defaultCommissionRate = 10
  settings.tempImageRetentionHours = 24
  settings.overdueOrderDays = 7
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.settings-container {
  padding: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}

.form-hint {
  width: 100%;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 4px;
}
</style>
