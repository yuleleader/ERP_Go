<template>
  <div class="statistics-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据统计</span>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <template v-else>
        <!-- 老板端统计 -->
        <template v-if="isBoss">
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon total-sales">
                  <el-icon><Money /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">¥{{ statistics.totalSales.toLocaleString() }}</div>
                  <div class="stat-label">订单总金额</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon order-count">
                  <el-icon><ShoppingCart /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.totalOrders }}</div>
                  <div class="stat-label">总订单数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon shipped">
                  <el-icon><CircleCheck /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.shippedOrders }}</div>
                  <div class="stat-label">已发货订单</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon pending">
                  <el-icon><Clock /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.pendingOrders }}</div>
                  <div class="stat-label">待发货订单</div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 平均发货时长 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon avg-shipping">
                  <el-icon><Timer /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ avgShippingTime.avg_days }}天</div>
                  <div class="stat-label">平均发货时长</div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 销售提成统计（按发货时间统计） -->
          <el-card style="margin-top: 20px;">
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
                    @change="fetchCommissionSummary"
                    style="width: 260px; margin-right: 10px;"
                  />
                  <el-select v-model="selectedUserId" placeholder="全部用户" clearable @change="fetchCommissionSummary" style="width: 150px; margin-right: 10px;">
                    <el-option label="全部用户" :value="null" />
                    <el-option v-for="user in salesUserList" :key="user.user_id" :label="user.real_name || user.username" :value="user.user_id" />
                  </el-select>
                  <div class="table-summary">
                    <span class="summary-item">总销售金额：<strong>¥{{ commissionSummary.total_sales.toLocaleString() }}</strong></span>
                    <span class="summary-item">退货金额：<strong>¥{{ commissionSummary.refund_amount.toLocaleString() }}</strong></span>
                    <span class="summary-item">总发货订单：<strong>{{ commissionSummary.shipped_count }}</strong> 单</span>
                    <span class="summary-item">退货订单：<strong>{{ commissionSummary.refunded_count }}</strong> 单</span>
                    <span class="summary-item">应发提成：<strong>¥{{ commissionSummary.due_commission.toLocaleString() }}</strong></span>
                    <span class="summary-item">实发提成：<strong>¥{{ commissionSummary.paid_commission.toLocaleString() }}</strong></span>
                  </div>
                </div>
              </div>
            </template>

            <el-table :data="commissionList" border style="width: 100%">
              <el-table-column prop="username" label="登录账号" width="120" />
              <el-table-column prop="real_name" label="真实姓名" width="120" />
              <el-table-column prop="commission_rate" label="提成比例" width="110">
                <template #default="scope">{{ scope.row.commission_rate }}%</template>
              </el-table-column>
              <el-table-column prop="total_sales" label="总销售金额" width="140">
                <template #default="scope">¥{{ scope.row.total_sales.toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="refund_amount" label="退货金额" width="140">
                <template #default="scope">¥{{ scope.row.refund_amount.toLocaleString() }}</template>
              </el-table-column>
              <el-table-column label="总发货订单数" width="130">
                <template #default="scope">
                  <span class="clickable-cell" @click="openOrderDialog(scope.row, 'shipped')">{{ scope.row.shipped_count }}</span>
                </template>
              </el-table-column>
              <el-table-column label="退货订单数" width="130">
                <template #default="scope">
                  <span class="clickable-cell danger" @click="openOrderDialog(scope.row, 'refunded')">{{ scope.row.refunded_count }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="due_commission" label="应发提成" width="140">
                <template #default="scope"><span class="commission-highlight">¥{{ scope.row.due_commission.toLocaleString() }}</span></template>
              </el-table-column>
              <el-table-column prop="paid_commission" label="实发提成" width="140">
                <template #default="scope">¥{{ scope.row.paid_commission.toLocaleString() }}</template>
              </el-table-column>
            </el-table>

            <div v-if="commissionList.length === 0" class="empty-state">
              <el-icon size="48" style="margin-bottom: 10px;"><User /></el-icon>
              <p>暂无提成数据</p>
            </div>
          </el-card>

          <!-- 提成订单明细弹窗（点击订单数弹出，非跳转） -->
          <el-dialog v-model="orderDialogVisible" :title="orderDialogTitle" width="82%" top="5vh">
            <div v-if="orderDialogLoading" class="loading-container">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>加载中...</span>
            </div>
            <template v-else>
              <el-table :data="orderDialogList" border max-height="60vh">
                <el-table-column prop="order_id" label="订单ID" width="200" />
                <el-table-column prop="platform_order_no" label="平台单号" width="180" />
                <el-table-column prop="product_name" label="商品名称" min-width="160" show-overflow-tooltip />
                <el-table-column prop="sales_amount" label="销售金额" width="120">
                  <template #default="scope">¥{{ scope.row.sales_amount.toLocaleString() }}</template>
                </el-table-column>
                <el-table-column prop="commission_amount" label="提成金额" width="120">
                  <template #default="scope">¥{{ scope.row.commission_amount.toLocaleString() }}</template>
                </el-table-column>
                <el-table-column label="发货状态" width="120">
                  <template #default="scope">
                    <el-tag
                      :type="scope.row.shipping_status === 'refunded' ? 'danger' : 'success'"
                      size="small"
                    >{{ scope.row.shipping_status === 'refunded' ? '已退货/退款' : (scope.row.shipping_status === 'virtual' ? '虚拟发货' : '已发货') }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="shipping_time" label="发货时间" width="170" />
                <el-table-column prop="refund_note" label="退款备注" min-width="160" show-overflow-tooltip />
              </el-table>
              <div v-if="orderDialogList.length === 0" class="empty-state">
                <p>该统计范围内暂无相关订单</p>
              </div>
            </template>
          </el-dialog>
        </template>

        <!-- 销售端统计 -->
        <template v-if="isSales">
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon total-sales">
                  <el-icon><Money /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">¥{{ statistics.totalSales.toLocaleString() }}</div>
                  <div class="stat-label">我的销售总金额</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon order-count">
                  <el-icon><ShoppingCart /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.totalOrders }}</div>
                  <div class="stat-label">我的订单数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon theoretical">
                  <el-icon><Wallet /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">¥{{ commissionStats.theoretical.toLocaleString() }}</div>
                  <div class="stat-label">理论应得提成</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon actual">
                  <el-icon><Wallet /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">¥{{ commissionStats.actual.toLocaleString() }}</div>
                  <div class="stat-label">实际应得提成</div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-card>
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
              <el-card>
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
        </template>

        <!-- 工厂端和发货端统计 -->
        <template v-if="isFactory || isShipping">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card class="stat-card">
                <div class="stat-icon order-count">
                  <el-icon><Box /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.totalOrders }}</div>
                  <div class="stat-label">总订单数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="stat-card">
                <div class="stat-icon pending">
                  <el-icon><Clock /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.pendingOrders }}</div>
                  <div class="stat-label">待处理订单</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="stat-card">
                <div class="stat-icon shipped">
                  <el-icon><CircleCheck /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ statistics.shippedOrders }}</div>
                  <div class="stat-label">已完成订单</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <div style="text-align: center; padding: 40px; color: #999;">
            <el-icon size="48" style="margin-bottom: 10px;"><PieChart /></el-icon>
            <p>暂无更多统计数据</p>
          </div>
        </template>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/store/user';
import { getOverviewStatistics, getTheoreticalCommission, getActualCommission, getSalesCommissionSummary, getCommissionOrders, getAvgShippingTime } from '@/api/statistics';
import { ElMessage } from 'element-plus';
import { formatDate } from '@/utils/format';
import { Money, ShoppingCart, CircleCheck, Clock, Wallet, InfoFilled, Box, PieChart, Loading, User, Timer } from '@element-plus/icons-vue';

const router = useRouter();
const userStore = useUserStore();

const isBoss = computed(() => userStore.role === 'boss');
const isSales = computed(() => userStore.role === 'sales');
const isFactory = computed(() => userStore.role === 'factory');
const isShipping = computed(() => userStore.role === 'shipping');

const loading = ref(false);

const statistics = reactive({
  totalSales: 0,
  totalOrders: 0,
  shippedOrders: 0,
  pendingOrders: 0
});

const commissionStats = reactive({
  theoretical: 0,
  theoreticalOrders: 0,
  actual: 0,
  actualOrders: 0
});

const commissionList = ref([]);
const commissionSummary = reactive({
  total_sales: 0,
  refund_amount: 0,
  shipped_count: 0,
  refunded_count: 0,
  due_commission: 0,
  paid_commission: 0
});
const selectedUserId = ref(null);
// 提成订单明细弹窗
const orderDialogVisible = ref(false);
const orderDialogLoading = ref(false);
const orderDialogTitle = ref('');
const orderDialogList = ref([]);
const salesUserList = ref([]);
const commissionDateRange = ref([]);
const theoreticalMonth = ref('');
const actualMonth = ref('');

const avgShippingTime = reactive({
  avg_days: 0,
  avg_hours: 0
});

const fetchStatistics = async () => {
  loading.value = true;
  try {
    const overview = await getOverviewStatistics();
    statistics.totalSales = overview.total_sales || 0;
    statistics.totalOrders = overview.total_orders || 0;
    statistics.shippedOrders = overview.shipped_orders || 0;
    statistics.pendingOrders = overview.pending_orders || 0;

    if (isSales.value) {
      await Promise.all([
        fetchTheoreticalCommission(),
        fetchActualCommission()
      ]);
    }

    if (isBoss.value) {
      await fetchCommissionSummary();
    }

    // 获取平均发货时长（所有角色都可以查看）
    const avgTime = await getAvgShippingTime();
    avgShippingTime.avg_days = avgTime.avg_days || 0;
    avgShippingTime.avg_hours = avgTime.avg_hours || 0;
  } catch (error) {
    console.error('获取统计数据失败:', error);
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录已过期，请重新登录');
      router.push('/login');
    } else {
      ElMessage.error('获取统计数据失败');
    }
  } finally {
    loading.value = false;
  }
};

const handleDateChange = () => {
  fetchStatistics();
};

const fetchTheoreticalCommission = async () => {
  try {
    let startDate = null;
    let endDate = null;
    
    if (theoreticalMonth.value) {
      const [year, month] = theoreticalMonth.value.split('-');
      const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate();
      startDate = `${year}-${month}-01`;
      endDate = `${year}-${month}-${daysInMonth}`;
    }
    
    const params = {};
    if (startDate && endDate) {
      params.start_date = startDate;
      params.end_date = endDate;
    }
    
    const result = await getTheoreticalCommission(params);
    commissionStats.theoretical = result.total_commission || 0;
    commissionStats.theoreticalOrders = result.order_count || 0;
  } catch (error) {
    console.error('获取理论提成失败:', error);
    ElMessage.error('获取理论提成失败');
  }
};

const fetchActualCommission = async () => {
  try {
    let startDate = null;
    let endDate = null;
    
    if (actualMonth.value) {
      const [year, month] = actualMonth.value.split('-');
      const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate();
      startDate = `${year}-${month}-01`;
      endDate = `${year}-${month}-${daysInMonth}`;
    }
    
    const params = {};
    if (startDate && endDate) {
      params.start_date = startDate;
      params.end_date = endDate;
    }
    
    const result = await getActualCommission(params);
    commissionStats.actual = result.total_commission || 0;
    commissionStats.actualOrders = result.order_count || 0;
  } catch (error) {
    console.error('获取实际提成失败:', error);
    ElMessage.error('获取实际提成失败');
  }
};

const fetchCommissionSummary = async () => {
  try {
    const params = {};
    if (commissionDateRange.value && commissionDateRange.value.length === 2) {
      params.start_date = commissionDateRange.value[0];
      params.end_date = commissionDateRange.value[1];
    }
    if (selectedUserId.value) {
      params.user_id = selectedUserId.value;
    }
    const result = await getSalesCommissionSummary(params);
    commissionList.value = result.data || [];
    commissionSummary.total_sales = result.summary?.total_sales || 0;
    commissionSummary.refund_amount = result.summary?.refund_amount || 0;
    commissionSummary.shipped_count = result.summary?.shipped_count || 0;
    commissionSummary.refunded_count = result.summary?.refunded_count || 0;
    commissionSummary.due_commission = result.summary?.due_commission || 0;
    commissionSummary.paid_commission = result.summary?.paid_commission || 0;
    salesUserList.value = result.data || [];
  } catch (error) {
    console.error('获取提成数据失败:', error);
    ElMessage.error('获取提成数据失败');
  }
};

// 点击"总发货订单数"或"退货订单数"弹出对应订单列表窗口
const openOrderDialog = async (row, type) => {
  orderDialogVisible.value = true;
  orderDialogLoading.value = true;
  orderDialogTitle.value = type === 'refunded'
    ? `${row.real_name || row.username} - 退货订单列表（已退货/退款）`
    : `${row.real_name || row.username} - 总发货订单列表（已发货 + 已退货/退款）`;
  orderDialogList.value = [];
  try {
    const params = {
      type,
      user_id: row.user_id
    };
    if (commissionDateRange.value && commissionDateRange.value.length === 2) {
      params.start_date = commissionDateRange.value[0];
      params.end_date = commissionDateRange.value[1];
    }
    const result = await getCommissionOrders(params);
    orderDialogList.value = result.data || [];
  } catch (error) {
    console.error('获取订单明细失败:', error);
    ElMessage.error('获取订单明细失败');
  } finally {
    orderDialogLoading.value = false;
  }
};

const initPage = async () => {
  if (!userStore.token) {
    router.push('/login');
    return;
  }

  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo();
    } catch (e) {
      console.error('获取用户信息失败:', e);
      router.push('/login');
      return;
    }
  }

  const now = new Date();
  const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

  const formatMonth = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
  };
  
  commissionDateRange.value = [formatDate(firstDayOfMonth), formatDate(now)];
  theoreticalMonth.value = formatMonth(now);
  actualMonth.value = formatMonth(now);

  fetchStatistics();
};

onMounted(() => {
  initPage();
});
</script>

<style scoped>
.statistics-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.date-filter {
  display: flex;
  gap: 10px;
  align-items: center;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #999;
}

.loading-container .el-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
  margin-right: 20px;
}

.stat-icon.total-sales { background: linear-gradient(135deg, #4facfe, #00f2fe); }
.stat-icon.order-count { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-icon.shipped { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.stat-icon.pending { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-icon.theoretical { background: linear-gradient(135deg, #fa709a, #fee140); }
.stat-icon.actual { background: linear-gradient(135deg, #a18cd1, #fbc2eb); }
.stat-icon.avg-shipping { background: linear-gradient(135deg, #4facfe, #00f2fe); }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
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

.table-header-right .el-select {
  width: 180px;
}

.table-header-right .el-date-picker {
  width: 260px;
}

.table-header-right .el-select .el-input__wrapper,
.table-header-right .el-date-picker .el-input__wrapper {
  padding-right: 30px;
}

.table-header-right .el-select-dropdown__item {
  height: 40px;
  line-height: 40px;
  padding: 0 16px;
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

.clickable-cell {
  color: #409EFF;
  cursor: pointer;
  font-weight: bold;
  text-decoration: underline;
}

.clickable-cell:hover {
  opacity: 0.8;
}

.clickable-cell.danger {
  color: #f56c6c;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #999;
}

.empty-state .el-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.commission-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>