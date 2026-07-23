<template>
  <div class="settings-container">
    <el-card class="mb-4">
      <template #header>
        <span>系统设置</span>
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

    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据清理管理</span>
        </div>
      </template>

      <el-tabs v-model="activeCleanupTab">
        <!-- 日志清理 -->
        <el-tab-pane label="日志清理" name="log">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="config-section">
                <h4>清理配置</h4>
                <el-form label-width="110px">
                  <el-form-item label="日志保留天数">
                    <el-input-number v-model="cleanupConfig.retentionDays" :min="30" :max="3650" />
                    <el-button type="primary" @click="updateConfig" style="margin-left: 10px">更新配置</el-button>
                  </el-form-item>
                  <el-form-item label="截止日期">
                    <span>{{ formatDateTime(cleanupConfig.cutoffDate) }}</span>
                  </el-form-item>
                  <el-form-item label="待删除日志">
                    <div>
                      <p>操作日志: <strong>{{ cleanupConfig.pendingDeletion?.operation || 0 }}</strong> 条</p>
                      <p>登录日志: <strong>{{ cleanupConfig.pendingDeletion?.login || 0 }}</strong> 条</p>
                      <p>总计: <strong>{{ cleanupConfig.pendingDeletion?.total || 0 }}</strong> 条</p>
                    </div>
                  </el-form-item>
                </el-form>
              </div>
            </el-col>

            <el-col :span="12">
              <div class="actions-section">
                <h4>清理操作</h4>
                <el-form label-width="100px">
                  <el-form-item label="清理类型">
                    <el-select v-model="cleanupType" style="width: 200px">
                      <el-option label="全部清理" value="all" />
                      <el-option label="仅清理操作日志" value="operation" />
                      <el-option label="仅清理登录日志" value="login" />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="info" @click="previewCleanup">预览清理</el-button>
                    <el-button type="warning" @click="confirmCleanup">执行清理</el-button>
                  </el-form-item>
                </el-form>

                <div class="schedule-info">
                  <el-alert type="info" :closable="false">
                    <template #title>
                      <p>📅 定时任务：每日凌晨2:00自动执行日志清理</p>
                    </template>
                  </el-alert>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 站内信清理 -->
        <el-tab-pane label="站内信清理" name="notification">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="config-section">
                <h4>清理配置</h4>
                <el-form label-width="110px">
                  <el-form-item label="保留天数">
                    <el-input-number v-model="notifConfig.retentionDays" :min="360" :max="3650" />
                    <el-button type="primary" @click="updateNotificationConfig" style="margin-left: 10px">更新配置</el-button>
                  </el-form-item>
                  <el-form-item label="截止日期">
                    <span>{{ formatDateTime(notifConfig.cutoffDate) }}</span>
                  </el-form-item>
                  <el-form-item label="待删除站内信">
                    <div>
                      <p>共: <strong>{{ notifConfig.pendingDeletion || 0 }}</strong> 条</p>
                      <p class="hint-text">（仅清除该日期之前、且已读或从未读但超期的站内信）</p>
                    </div>
                  </el-form-item>
                </el-form>
              </div>
            </el-col>

            <el-col :span="12">
              <div class="actions-section">
                <h4>清理操作</h4>
                <el-form label-width="100px">
                  <el-form-item>
                    <el-button type="info" @click="previewNotificationCleanup">预览清理</el-button>
                    <el-button type="warning" @click="confirmNotificationCleanup">执行清理</el-button>
                  </el-form-item>
                </el-form>

                <div class="schedule-info">
                  <el-alert type="info" :closable="false">
                    <template #title>
                      <p>📅 定时任务：每日凌晨2:10自动执行站内信清理</p>
                      <p>📌 站内信默认最少存储 360 天</p>
                    </template>
                  </el-alert>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>

      <div class="records-section">
        <h4>清理记录</h4>
        <el-table :data="cleanupRecords" v-loading="recordsLoading" style="width: 100%">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="cleanup_type" label="清理类型" width="120">
            <template #default="scope">
              <el-tag v-if="scope.row.cleanup_type === 'all'">全部清理</el-tag>
              <el-tag v-else-if="scope.row.cleanup_type === 'operation'" type="success">操作日志</el-tag>
              <el-tag v-else-if="scope.row.cleanup_type === 'login'" type="info">登录日志</el-tag>
              <el-tag v-else-if="scope.row.cleanup_type === 'notification'" type="warning">站内信</el-tag>
              <el-tag v-else>{{ scope.row.cleanup_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="retention_days" label="保留天数" width="100" />
          <el-table-column prop="deleted_count" label="删除数量" width="100" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag v-if="scope.row.status === 'success'" type="success">成功</el-tag>
              <el-tag v-else-if="scope.row.status === 'failed'" type="danger">失败</el-tag>
              <el-tag v-else type="warning">进行中</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="triggered_by" label="触发方式" width="100">
            <template #default="scope">
              <el-tag v-if="scope.row.triggered_by === 'manual'">手动</el-tag>
              <el-tag v-else type="info">定时</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="operator_username" label="操作者" width="120" />
          <el-table-column label="开始时间" width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.start_time) }}
            </template>
          </el-table-column>
          <el-table-column label="结束时间" width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.end_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>
    </el-card>

    <el-card style="margin-top: 20px;">
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
import { formatDate, formatDateTime } from '@/utils/format'
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import {
  getCleanupConfig,
  updateCleanupConfig,
  previewCleanup as previewLogCleanup,
  executeCleanup as executeLogCleanup,
  getCleanupRecords,
  getNotificationCleanupConfig,
  updateNotificationCleanupConfig,
  previewNotificationCleanup as previewNotifCleanup,
  executeNotificationCleanup as executeNotifCleanup
} from '@/api/logs'

const settings = reactive({
  defaultCommissionRate: 10,
  tempImageRetentionHours: 24
})

const recordsLoading = ref(false)
const cleanupRecords = ref([])
const cleanupType = ref('all')
const activeCleanupTab = ref('log')

const cleanupConfig = reactive({
  retentionDays: 730,
  cutoffDate: null,
  pendingDeletion: null
})

const notifConfig = reactive({
  retentionDays: 360,
  cutoffDate: null,
  pendingDeletion: 0
})


function saveSettings() {
  localStorage.setItem('systemSettings', JSON.stringify(settings))
  ElMessage.success('设置保存成功')
}

function resetSettings() {
  settings.defaultCommissionRate = 10
  settings.tempImageRetentionHours = 24
}

// ==================== 日志清理 ====================

async function fetchCleanupConfig() {
  try {
    const config = await getCleanupConfig()
    cleanupConfig.retentionDays = config.retention_days
    cleanupConfig.cutoffDate = config.cutoff_date
    cleanupConfig.pendingDeletion = config.pending_deletion
  } catch (error) {
    ElMessage.error('获取清理配置失败')
  }
}

async function updateConfig() {
  try {
    await updateCleanupConfig({
      retention_days: cleanupConfig.retentionDays
    })
    ElMessage.success('配置更新成功')
    await fetchCleanupConfig()
  } catch (error) {
    ElMessage.error('更新配置失败')
  }
}

async function previewCleanup() {
  try {
    const result = await previewLogCleanup({
      retention_days: cleanupConfig.retentionDays
    })
    ElMessage.success(
      `预览完成\n操作日志: ${result.operation_logs} 条\n登录日志: ${result.login_logs} 条\n总计: ${result.total_logs} 条`
    )
  } catch (error) {
    ElMessage.error('预览失败')
  }
}

async function confirmCleanup() {
  try {
    await ElMessageBox.confirm(
      `确定要执行${cleanupType.value === 'all' ? '全部' : cleanupType.value === 'operation' ? '操作日志' : '登录日志'}清理吗？\n此操作不可恢复！`,
      '重要确认',
      {
        confirmButtonText: '确认清理',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const result = await executeLogCleanup({
      cleanup_type: cleanupType.value,
      confirm: true
    })

    ElMessage.success(`清理完成，共删除 ${result.deleted_count} 条记录`)
    await fetchCleanupConfig()
    await fetchCleanupRecords()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '清理失败')
    }
  }
}

// ==================== 站内信清理 ====================

async function fetchNotificationCleanupConfig() {
  try {
    const config = await getNotificationCleanupConfig()
    notifConfig.retentionDays = config.retention_days
    notifConfig.cutoffDate = config.cutoff_date
    notifConfig.pendingDeletion = config.pending_deletion
  } catch (error) {
    ElMessage.error('获取站内信清理配置失败')
  }
}

async function updateNotificationConfig() {
  try {
    await updateNotificationCleanupConfig({
      retention_days: notifConfig.retentionDays
    })
    ElMessage.success('配置更新成功')
    await fetchNotificationCleanupConfig()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新配置失败')
  }
}

async function previewNotificationCleanup() {
  try {
    const result = await previewNotifCleanup({
      retention_days: notifConfig.retentionDays
    })
    ElMessage.success(
      `预览完成\n待删除站内信: ${result.total_notifications} 条`
    )
  } catch (error) {
    ElMessage.error('预览失败')
  }
}

async function confirmNotificationCleanup() {
  try {
    await ElMessageBox.confirm(
      '确定要执行站内信清理吗？\n此操作不可恢复！',
      '重要确认',
      {
        confirmButtonText: '确认清理',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const result = await executeNotifCleanup({ confirm: true })

    ElMessage.success(`清理完成，共删除 ${result.deleted_count} 条站内信`)
    await fetchNotificationCleanupConfig()
    await fetchCleanupRecords()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '清理失败')
    }
  }
}

// ==================== 清理记录 ====================

async function fetchCleanupRecords() {
  recordsLoading.value = true
  try {
    cleanupRecords.value = await getCleanupRecords()
  } catch (error) {
    ElMessage.error('获取清理记录失败')
  } finally {
    recordsLoading.value = false
  }
}

const savedSettings = localStorage.getItem('systemSettings')
if (savedSettings) {
  Object.assign(settings, JSON.parse(savedSettings))
}

onMounted(() => {
  fetchCleanupConfig()
  fetchNotificationCleanupConfig()
  fetchCleanupRecords()
})
</script>

<style scoped>
.settings-container {
  padding: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}

.card-header {
  font-weight: 600;
}

.config-section,
.actions-section {
  padding: 10px;
}

.config-section h4,
.actions-section h4,
.records-section h4 {
  margin: 0 0 20px 0;
  color: #303133;
}

.hint-text {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.records-section {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.schedule-info {
  margin-top: 20px;
}
</style>
