<template>
  <div class="commission-stats-container">
    <!-- 销售端：理论/实际提成对比 -->
    <el-card v-if="isSales" style="margin-bottom: 20px;">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div class="commission-card-header">
                <span>理论应得提成（按销售时间统计）</span>
                <el-date-picker
                  v-model="theoreticalMonth"
                  type="month"
                  format="YYYY年MM月"
                  value-format="YYYY-MM"
                  @change="fetchTheoreticalCommission"
                  style="width: 150px;"
                />
              </div>
            </template>
            <div class="commission-detail">
              <div class="commission-amount">
                <span class="amount-label">提成金额</span>
                <span class="amount-value theoretical">¥{{ commissionStats.theoretical.toLocaleString() }}</span>
              </div>
              <div class="commission-info">
                <span>统计期间订单数：{{ commissionStats.theoreticalOrders }} 单</span>
              </div>
              <div class="commission-note">
                <el-icon><InfoFilled /></el-icon>
                <span>理论应得提成：根据订单创建时间统计，包含所有已创建的订单提成</span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>
              <div class="commission-card-header">
                <span>实际应得提成（按发货时间统计）</span>
                <el-date-picker
                  v-model="actualMonth"
                  type="month"
                  format="YYYY年MM月"
                  value-format="YYYY-MM"
                  @change="fetchActualCommission"
                  style="width: 150px;"
                />
              </div>
            </template>
            <div class="commission-detail">
              <div class="commission-amount">
                <span class="amount-label">提成金额</span>
                <span class="amount-value actual">¥{{ commissionStats.actual.toLocaleString() }}</span>
              </div>
              <div class="commission-info">
                <span>统计期间发货订单数：{{ commissionStats.actualOrders }} 单</span>
              </div>
              <div class="commission-note">
                <el-icon><InfoFilled /></el-icon>
                <span>实际应得提成：根据订单发货时间统计，仅包含已发货的订单提成</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 老板端：按发货时间的销售提成统计表 -->
    <el-card v-if="isBoss">
      <template #header>
        <div class="table-header">
          <span>销售提成统计（按发货时间统计）</span>
          <div class="table-header-right">
            <el-date-picker
              v-model="commissionDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="fetchCommissionByUser"
              style="width: 260px; margin-right: 10px;"
            />
            <el-select v-model="selectedUserId" placeholder="全部用户" clearable @change="fetchCommissionByUser" style="width: 150px; margin-right: 10px;">
              <el-option label="全部用户" :value="null" />
              <el-option v-for="user in salesUserList" :key="user.user_id" :label="user.real_name || user.username" :value="user.user_id" />
            </el-select>
            <div class="table-summary">
              <span class="summary-item">
                总计提成：<strong>¥{{ commissionByUserSummary.total_commission.toLocaleString() }}</strong>
              </span>
              <span class="summary-item">
                总计订单：<strong>{{ commissionByUserSummary.total_orders }}</strong> 单
              </span>
              <span class="summary-item">
                总计销售：<strong>¥{{ commissionByUserSummary.total_sales.toLocaleString() }}</strong>
              </span>
            </div>
          </div>
        </div>
      </template>

      <el-table :data="commissionByUserList" border style="width: 100%">
        <el-table-column prop="username" label="登录账号" width="120" />
        <el-table-column prop="real_name" label="真实姓名" width="120" />
        <el-table-column prop="commission_rate" label="提成比例" width="120">
          <template #default="scope">
            {{ scope.row.commission_rate }}%
          </template>
        </el-table-column>
        <el-table-column prop="total_sales" label="销售金额" width="140">
          <template #default="scope">
            ¥{{ scope.row.total_sales.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="order_count" label="发货订单数" width="120" />
        <el-table-column prop="total_commission" label="应得提成" width="140">
          <template #default="scope">
            <span class="commission-highlight">¥{{ scope.row.total_commission.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="avg_commission" label="单笔提成" width="120">
          <template #default="scope">
            ¥{{ scope.row.avg_commission.toLocaleString() }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="commissionByUserList.length === 0" class="empty-state">
        <el-icon size="48" style="margin-bottom: 10px;"><User /></el-icon>
        <p>暂无提成数据</p>
      </div>
    </el-card>

    <el-card v-if="isFactory || isShipping" class="no-permission">
      <el-icon size="48"><Lock /></el-icon>
      <p>销售提成统计仅老板端与销售端可见</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { getTheoreticalCommission, getActualCommission, getCommissionByUser } from '@/api/statistics'
import { ElMessage } from 'element-plus'
import { formatDate } from '@/utils/format'
import { InfoFilled, User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const isBoss = userStore.role === 'boss'
const isSales = userStore.role === 'sales'
const isFactory = userStore.role === 'factory'
const isShipping = userStore.role === 'shipping'

const commissionStats = reactive({
  theoretical: 0,
  theoreticalOrders: 0,
  actual: 0,
  actualOrders: 0
})

const commissionByUserList = ref([])
const commissionByUserSummary = reactive({
  total_commission: 0,
  total_orders: 0,
  total_sales: 0
})
const selectedUserId = ref(null)
const salesUserList = ref([])
const commissionDateRange = ref([])
const theoreticalMonth = ref('')
const actualMonth = ref('')

const fetchTheoreticalCommission = async () => {
  try {
    let startDate = null
    let endDate = null
    if (theoreticalMonth.value) {
      const [year, month] = theoreticalMonth.value.split('-')
      const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate()
      startDate = `${year}-${month}-01`
      endDate = `${year}-${month}-${daysInMonth}`
    }
    const params = {}
    if (startDate && endDate) {
      params.start_date = startDate
      params.end_date = endDate
    }
    const result = await getTheoreticalCommission(params)
    commissionStats.theoretical = result.total_commission || 0
    commissionStats.theoreticalOrders = result.order_count || 0
  } catch (error) {
    ElMessage.error('获取理论提成失败')
  }
}

const fetchActualCommission = async () => {
  try {
    let startDate = null
    let endDate = null
    if (actualMonth.value) {
      const [year, month] = actualMonth.value.split('-')
      const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate()
      startDate = `${year}-${month}-01`
      endDate = `${year}-${month}-${daysInMonth}`
    }
    const params = {}
    if (startDate && endDate) {
      params.start_date = startDate
      params.end_date = endDate
    }
    const result = await getActualCommission(params)
    commissionStats.actual = result.total_commission || 0
    commissionStats.actualOrders = result.order_count || 0
  } catch (error) {
    ElMessage.error('获取实际提成失败')
  }
}

const fetchCommissionByUser = async () => {
  try {
    const params = {}
    if (commissionDateRange.value && commissionDateRange.value.length === 2) {
      params.start_date = commissionDateRange.value[0]
      params.end_date = commissionDateRange.value[1]
    }
    if (selectedUserId.value) {
      params.user_id = selectedUserId.value
    }
    const result = await getCommissionByUser(params)
    if (selectedUserId.value) {
      const filteredData = result.data.filter(item => item.user_id === selectedUserId.value)
      commissionByUserList.value = filteredData.map(item => ({
        ...item,
        avg_commission: item.order_count > 0 ? (item.total_commission / item.order_count).toFixed(2) : '0.00'
      }))
      commissionByUserSummary.total_commission = filteredData.reduce((sum, item) => sum + item.total_commission, 0)
      commissionByUserSummary.total_orders = filteredData.reduce((sum, item) => sum + item.order_count, 0)
      commissionByUserSummary.total_sales = filteredData.reduce((sum, item) => sum + item.total_sales, 0)
    } else {
      commissionByUserList.value = result.data.map(item => ({
        ...item,
        avg_commission: item.order_count > 0 ? (item.total_commission / item.order_count).toFixed(2) : '0.00'
      }))
      commissionByUserSummary.total_commission = result.summary?.total_commission || 0
      commissionByUserSummary.total_orders = result.summary?.total_orders || 0
      commissionByUserSummary.total_sales = result.summary?.total_sales || 0
    }
  } catch (error) {
    ElMessage.error('获取提成数据失败')
  }
}

onMounted(async () => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch (e) {
      router.push('/login')
      return
    }
  }

  const now = new Date()
  const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
  const formatMonth = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`

  commissionDateRange.value = [formatDate(firstDayOfMonth), formatDate(now)]
  theoreticalMonth.value = formatMonth(now)
  actualMonth.value = formatMonth(now)

  if (isSales.value) {
    await Promise.all([fetchTheoreticalCommission(), fetchActualCommission()])
  }
  if (isBoss.value) {
    await fetchCommissionByUser()
  }
})
</script>

<style scoped>
.commission-stats-container {
  padding: 20px;
}

.commission-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.commission-detail {
  padding: 10px;
}

.commission-amount {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.amount-label {
  font-size: 14px;
  color: #666;
}

.amount-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
}

.amount-value.theoretical {
  color: #fa709a;
}

.amount-value.actual {
  color: #a18cd1;
}

.commission-info {
  font-size: 14px;
  color: #666;
  margin-bottom: 15px;
}

.commission-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #999;
  padding: 10px;
  background: #fafafa;
  border-radius: 4px;
}

.commission-note .el-icon {
  font-size: 14px;
  color: #409EFF;
  flex-shrink: 0;
  margin-top: 2px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.table-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.table-summary {
  display: flex;
  gap: 20px;
}

.summary-item {
  font-size: 14px;
  color: #666;
}

.summary-item strong {
  color: #409EFF;
}

.commission-highlight {
  color: #fa709a;
  font-weight: bold;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #999;
}

.no-permission {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #999;
  gap: 12px;
}
</style>
