<template>
  <div class="commission-settlement">
    <div class="search-bar">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="结算月份">
          <el-date-picker
            v-model="searchForm.month"
            type="month"
            placeholder="选择月份"
            format="YYYY-MM"
            value-format="YYYY-MM"
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="summary-cards" v-if="summaryData">
      <el-card class="summary-card">
        <div class="summary-item">
          <span class="summary-label">结算月份</span>
          <span class="summary-value">{{ summaryData.month }}</span>
        </div>
      </el-card>
      <el-card class="summary-card">
        <div class="summary-item">
          <span class="summary-label">应发提成总额</span>
          <span class="summary-value text-primary">¥{{ summaryData.total_amount.toFixed(2) }}</span>
        </div>
      </el-card>
      <el-card class="summary-card">
        <div class="summary-item">
          <span class="summary-label">订单数量</span>
          <span class="summary-value">{{ summaryData.total_orders }}</span>
        </div>
      </el-card>
      <el-card class="summary-card">
        <div class="summary-item">
          <span class="summary-label">销售金额</span>
          <span class="summary-value">¥{{ summaryData.total_sales.toFixed(2) }}</span>
        </div>
      </el-card>
    </div>

    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>提成结算列表</span>
          <el-button
            type="success"
            @click="handlePayAll"
            :disabled="!summaryData || summaryData.total_amount <= 0"
          >
            批量发放全部提成
          </el-button>
        </div>
      </template>

      <el-table :data="summaryData?.users || []" border>
        <el-table-column prop="real_name" label="销售姓名" />
        <el-table-column prop="username" label="账号" />
        <el-table-column prop="total_sales" label="销售金额" width="120">
          <template #default="{ row }">
            ¥{{ row.total_sales.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="order_count" label="订单数量" width="100" />
        <el-table-column prop="total_commission" label="应发提成" width="120">
          <template #default="{ row }">
            <span class="commission-amount">¥{{ row.total_commission.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="viewOrderDetail(row)">查看明细</el-button>
            <el-button
              size="small"
              type="success"
              @click="handlePaySingle(row)"
              :disabled="row.total_commission <= 0"
            >
              发放提成
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!summaryData || summaryData.users.length === 0" class="empty-tip">
        暂无数据
      </div>
    </el-card>

    <el-dialog
      v-model="orderDialogVisible"
      title="订单明细"
      width="800px"
      @close="orderDialogVisible = false"
    >
      <el-table :data="orderDetailList" border>
        <el-table-column prop="platform_order_no" label="平台订单号" />
        <el-table-column prop="product_name" label="商品名称" />
        <el-table-column prop="sales_amount" label="销售金额" width="120">
          <template #default="{ row }">
            ¥{{ row.sales_amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="commission_amount" label="提成金额" width="120">
          <template #default="{ row }">
            ¥{{ row.commission_amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="shipping_time" label="发货时间" width="160" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { commissionSettlementApi } from '@/api'

const searchForm = reactive({
  month: ''
})

const summaryData = ref(null)
const orderDetailList = ref([])
const orderDialogVisible = ref(false)
const currentUser = ref(null)

const handleSearch = async () => {
  if (!searchForm.month) {
    ElMessage.warning('请选择结算月份')
    return
  }

  try {
    const res = await commissionSettlementApi.getUnpaidCommission(searchForm.month)
    if (res.code === 200) {
      summaryData.value = res.data
    }
  } catch (error) {
    ElMessage.error('查询失败')
  }
}

const viewOrderDetail = async (row) => {
  try {
    const res = await commissionSettlementApi.getUnpaidOrders(searchForm.month, row.username)
    if (res.code === 200) {
      orderDetailList.value = res.data
      orderDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error('查询失败')
  }
}

const handlePaySingle = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认发放 ${row.real_name}（${searchForm.month}）的提成 ¥${row.total_commission.toFixed(2)} 吗？`,
      '确认发放',
      { type: 'warning' }
    )

    const res = await commissionSettlementApi.payCommission(searchForm.month, row.username)
    if (res.code === 200) {
      ElMessage.success('发放成功')
      handleSearch()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '发放失败')
    }
  }
}

const handlePayAll = async () => {
  try {
    await ElMessageBox.confirm(
      `确认发放 ${searchForm.month} 月份所有销售的提成，总计 ¥${summaryData.value.total_amount.toFixed(2)} 吗？`,
      '确认批量发放',
      { type: 'warning' }
    )

    const res = await commissionSettlementApi.payCommission(searchForm.month, null)
    if (res.code === 200) {
      ElMessage.success('批量发放成功')
      handleSearch()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '发放失败')
    }
  }
}

const init = () => {
  const now = new Date()
  searchForm.month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  handleSearch()
}

onMounted(() => {
  init()
})
</script>

<style scoped>
.commission-settlement {
  padding: 20px;
}

.search-bar {
  margin-bottom: 20px;
}

.search-form {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-cards {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.summary-card {
  flex: 1;
  min-width: 180px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.summary-label {
  font-size: 14px;
  color: #999;
}

.summary-value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

.text-primary {
  color: #409eff;
}

.main-card {
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.commission-amount {
  color: #e6a23c;
  font-weight: bold;
}

.empty-tip {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>