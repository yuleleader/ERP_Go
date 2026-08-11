<template>
  <div class="system-backup-page">
    <!-- 启动器未连接提示 -->
    <el-alert
      v-if="!connected"
      type="warning"
      :closable="false"
      show-icon
      title="桌面启动器未运行"
      description="系统备份功能需要桌面启动器提供本地备份服务。请先启动「订单管理系统启动器」，再刷新本页。"
      style="margin-bottom: 16px;"
    />

    <div class="row">
      <!-- 左：备份状态与操作 -->
      <el-card class="panel" shadow="never">
        <template #header>
          <div class="panel-header">
            <span>备份状态</span>
            <el-tag :type="connected ? 'success' : 'danger'" size="small">
              {{ connected ? '启动器已连接' : '启动器未连接' }}
            </el-tag>
          </div>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="备份目录">
            {{ state.backup_dir || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="自动备份">
            <el-tag :type="autoBackup.enabled ? 'success' : 'info'" size="small">
              {{ autoBackup.enabled ? '已启用' : '未启用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="下次备份时间">
            {{ state.next_backup || '—' }}
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 16px;">
          <el-button
            type="primary"
            :loading="running"
            :disabled="!connected"
            @click="handleRunBackup"
          >
            立即备份
          </el-button>
          <span class="hint">点击后由桌面启动器执行数据库备份</span>
        </div>
      </el-card>

      <!-- 右：自动备份设置 -->
      <el-card class="panel" shadow="never">
        <template #header>
          <span>自动备份设置</span>
        </template>
        <el-form label-width="90px">
          <el-form-item label="启用自动备份">
            <el-switch v-model="form.enabled" :disabled="!connected" />
          </el-form-item>
          <el-form-item label="备份模式">
            <el-select v-model="form.period" :disabled="!connected" style="width: 100%;">
              <el-option label="每日" value="daily" />
              <el-option label="每周" value="weekly" />
              <el-option label="每月" value="monthly" />
              <el-option label="每隔几小时" value="interval" />
            </el-select>
          </el-form-item>
          <el-form-item label="执行时间">
            <el-select v-model="form.time" :disabled="!connected" style="width: 100%;">
              <el-option
                v-for="t in timeOptions"
                :key="t"
                :label="t"
                :value="t"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.period === 'weekly'" label="星期">
            <el-select v-model="form.weekday" :disabled="!connected" style="width: 100%;">
              <el-option
                v-for="(w, i) in weekLabels"
                :key="i"
                :label="w"
                :value="i"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.period === 'monthly'" label="日期">
            <el-select v-model="form.day" :disabled="!connected" style="width: 100%;">
              <el-option
                v-for="d in 31"
                :key="d"
                :label="`${d} 日`"
                :value="d"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.period === 'interval'" label="间隔小时">
            <el-input-number v-model="form.interval" :min="1" :max="24" :disabled="!connected" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" :disabled="!connected" @click="handleSaveConfig">
              保存设置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 备份日志 -->
    <el-card class="panel" shadow="never" style="margin-top: 16px;">
      <template #header>
        <div class="panel-header">
          <span>备份日志（最近 {{ logs.length }} 条，每 5 秒自动刷新）</span>
          <el-button size="small" @click="loadState">刷新</el-button>
        </div>
      </template>
      <el-table :data="logs" v-loading="loading" border style="width: 100%;" empty-text="暂无备份日志">
        <el-table-column prop="ts" label="时间" width="180" />
        <el-table-column label="级别" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" size="small">{{ levelText(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="text" label="内容" min-width="300" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
defineOptions({ name: 'SystemBackup' })
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getBackupState, runBackupNow, saveBackupConfig } from '@/api/systemBackup'

const loading = ref(false)
const running = ref(false)
const saving = ref(false)
const connected = ref(false)
const state = reactive({ backup_dir: '', next_backup: '', auto_backup: {} })
const logs = ref([])

const timeOptions = []
for (let h = 0; h < 24; h++) {
  for (const m of [0, 30]) {
    timeOptions.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`)
  }
}
const weekLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const form = reactive({
  enabled: false,
  period: 'daily',
  time: '02:00',
  weekday: 0,
  day: 1,
  interval: 4
})

const autoBackup = computed(() => state.auto_backup || {})

function levelText(level) {
  const map = { success: '成功', warning: '警告', error: '错误', system: '系统', info: '信息' }
  return map[level] || level || '信息'
}

function levelType(level) {
  const map = { success: 'success', warning: 'warning', error: 'danger', system: 'primary', info: 'info' }
  return map[level] || 'info'
}

function fillForm(ac) {
  if (!ac) return
  form.enabled = !!ac.enabled
  form.period = ac.period || 'daily'
  form.time = ac.time || '02:00'
  form.weekday = Number.isInteger(ac.weekday) ? ac.weekday : 0
  form.day = Number.isInteger(ac.day) ? ac.day : 1
  form.interval = Number.isInteger(ac.interval) ? ac.interval : 4
}

async function loadState() {
  loading.value = true
  try {
    const res = await getBackupState()
    connected.value = !!res.ok
    if (res.ok) {
      state.backup_dir = res.backup_dir || ''
      state.next_backup = res.next_backup || ''
      state.auto_backup = res.auto_backup || {}
      logs.value = Array.isArray(res.logs) ? res.logs.slice().reverse() : []
      fillForm(res.auto_backup)
    }
  } catch (e) {
    connected.value = false
  } finally {
    loading.value = false
  }
}

async function handleRunBackup() {
  running.value = true
  try {
    const res = await runBackupNow()
    ElMessage.success(res.message || '已触发立即备份')
    setTimeout(loadState, 800)
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '触发备份失败')
  } finally {
    running.value = false
  }
}

async function handleSaveConfig() {
  saving.value = true
  try {
    const payload = { auto_backup: { ...form } }
    const res = await saveBackupConfig(payload)
    ElMessage.success(res.message || '自动备份设置已保存')
    loadState()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

let timer = null
onMounted(() => {
  loadState()
  timer = setInterval(loadState, 5000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.system-backup-page {
  padding: 4px;
}

.row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.panel {
  flex: 1;
  min-width: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}
</style>
