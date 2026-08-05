<template>
  <div class="system-controls">
    <div class="control-section">
      <h3>数据更新</h3>
      <div class="status">
        <span class="status-dot" :class="updateStatus"></span>
        <span>{{ updateStatusText }}</span>
      </div>
      <span class="time">最后更新: {{ lastUpdateTime }}</span>
      <el-button type="primary" size="small" @click="refreshData">
        刷新数据
      </el-button>
    </div>
    
    <div class="control-section">
      <h3>异常预警</h3>
      <div v-if="alerts.length > 0" class="alerts">
        <div 
          v-for="(alert, index) in alerts" 
          :key="index"
          class="alert-item"
          :class="alert.level"
        >
          <span>{{ alert.title }}</span>
        </div>
      </div>
      <div v-else class="no-alerts">
        <span>暂无异常</span>
      </div>
    </div>
    
    <div class="control-section">
      <h3>时间范围</h3>
      <el-date-picker 
        v-model="dateRange" 
        type="daterange" 
        range-separator="至" 
        start-placeholder="开始"
        end-placeholder="结束"
        size="small"
      />
    </div>
    
    <div class="control-section">
      <h3>数据导出</h3>
      <el-button type="text" size="small" @click="exportData('excel')">Excel</el-button>
      <el-button type="text" size="small" @click="exportData('png')">PNG</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  lastUpdate: {
    type: String,
    default: '--'
  }
})

const emit = defineEmits(['refresh', 'dateChange', 'export'])

const updateStatus = ref('online')
const updateStatusText = ref('在线')
const lastUpdateTime = ref('--')
const dateRange = ref([])
const alerts = ref([
  { level: 'warning', title: '待发货订单超过阈值' }
])

watch(() => props.lastUpdate, (newVal) => {
  if (newVal) {
    lastUpdateTime.value = newVal
  }
})

function refreshData() {
  updateStatus.value = 'refreshing'
  updateStatusText.value = '刷新中...'
  setTimeout(() => {
    updateStatus.value = 'online'
    updateStatusText.value = '在线'
    emit('refresh')
  }, 1000)
}

function exportData(format) {
  emit('export', format)
}

onMounted(() => {
  lastUpdateTime.value = props.lastUpdate || new Date().toLocaleTimeString()
})
</script>

<style scoped>
.system-controls {
  background: #1a2332;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #334155;
}

.control-section {
  margin-bottom: 20px;
  
  &:last-child {
    margin-bottom: 0;
  }
}

h3 {
  color: #60a5fa;
  font-size: 14px;
  margin-bottom: 12px;
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  
  &.online { background: #10b981; }
  &.refreshing { background: #f59e0b; animation: pulse 1s infinite; }
  &.offline { background: #ef4444; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.time {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 12px;
}

.alerts {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-item {
  padding: 8px;
  border-radius: 6px;
  font-size: 12px;
  
  &.warning {
    background: rgba(245, 158, 11, 0.2);
    color: #f59e0b;
  }
  &.severe {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }
}

.no-alerts {
  padding: 12px;
  text-align: center;
  color: #64748b;
  font-size: 12px;
}
</style>