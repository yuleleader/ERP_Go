<template>
  <div class="logs-container">
    <el-card class="mb-4">
      <template #header>
        <span>操作日志</span>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="用户名">
          <el-input v-model="filters.username" placeholder="请输入用户名" clearable @change="fetchLogs" style="width: 200px" />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="filters.operationType" placeholder="请选择" clearable @change="fetchLogs" style="width: 150px">
            <el-option label="登录" value="登录" />
            <el-option label="创建订单" value="创建订单" />
            <el-option label="更新订单" value="更新订单" />
            <el-option label="删除订单" value="删除订单" />
            <el-option label="上传图片" value="上传图片" />
            <el-option label="删除图片" value="删除图片" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchLogs">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="logs" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="real_name" label="用户名" width="120" />
        <el-table-column prop="operation_type" label="操作类型" width="120" />
        <el-table-column prop="operation_content" label="操作内容" min-width="300" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP地址" width="150" />
        <el-table-column label="操作时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { formatDate, formatDateTime } from '@/utils/format'
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const logs = ref([])

const filters = reactive({
  username: '',
  operationType: ''
})

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})


function handleSizeChange(newSize) {
  pagination.page = 1
  pagination.limit = newSize
  fetchLogs()
}

function handlePageChange(newPage) {
  pagination.page = newPage
  fetchLogs()
}

async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit
    }
    if (filters.username) params.username = filters.username
    if (filters.operationType) params.operation_type = filters.operationType

    const response = await request({ url: '/logs/operations', method: 'get', params })
    logs.value = response.items
    pagination.total = response.total
  } catch (error) {
    ElMessage.error('获取日志列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.logs-container {
  padding: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}

.filter-form {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 16px 0;
  background: #fff;
  border-top: 1px solid #ebeef5;
  position: relative;
  z-index: 10;
}
</style>
