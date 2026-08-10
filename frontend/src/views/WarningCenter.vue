<template>
  <div class="warning-center">
    <!-- 顶部统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card unproduced">
        <div class="stat-icon"><el-icon :size="30"><Warning /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ data.total_unproduced }}</div>
          <div class="stat-label">超期未生产（单）</div>
        </div>
      </div>
      <div class="stat-card unsent">
        <div class="stat-icon"><el-icon :size="30"><Van /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ data.total_unsent }}</div>
          <div class="stat-label">超期未发货（单）</div>
        </div>
      </div>
      <div class="stat-card sales">
        <div class="stat-icon"><el-icon :size="30"><User /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ data.sales_count }}</div>
          <div class="stat-label">涉及销售员（人）</div>
        </div>
      </div>
    </div>

    <!-- 筛选区 -->
    <el-card class="list-card" ref="cardRef">
      <template #header>
        <div class="card-header">
          <span>预警明细（超期 {{ data.overdue_days }} 天，即下单超过该天数仍未发货/未生产完成）</span>
          <div class="filter-right">
            <el-input-number v-model="days" :min="1" :max="365" size="small" style="width: 100px" />
            <el-button size="small" type="primary" @click="fetchWarnings">查询</el-button>
            <el-button size="small" @click="goOrders">去订单列表处理</el-button>
          </div>
        </div>
      </template>

      <!-- 销售员分组 -->
      <div v-loading="loading">
        <div v-if="!groups.length" class="empty-tip">
          <el-empty description="暂无超期预警，太棒了！" />
        </div>
        <div v-for="g in groups" :key="g.username" class="sales-group">
          <div class="group-header">
            <span class="group-name">{{ g.sales_person }}</span>
            <el-tag type="danger" size="small" class="group-tag">超期未生产 {{ g.unproduced_count }}</el-tag>
            <el-tag type="warning" size="small" class="group-tag">超期未发货 {{ g.unsent_count }}</el-tag>
          </div>
          <el-table ref="tableRef" :data="g.unsent" border size="small" class="group-table" @row-click="row => goOrder(row)">
            <el-table-column label="序号" min-width="55" align="center">
              <template #default="{ $index }">{{ $index + 1 }}</template>
            </el-table-column>
            <el-table-column prop="platform_order_no" label="平台订单号" min-width="130" show-overflow-tooltip />
            <el-table-column prop="product_name" label="商品名称" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">{{ row.product_name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="shop_name" label="网店" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">{{ row.shop_name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="sales_amount" label="销售金额" min-width="95" align="right">
              <template #default="{ row }">{{ row.sales_amount ? '¥' + row.sales_amount : '—' }}</template>
            </el-table-column>
            <el-table-column label="下单时间" min-width="140" align="center">
              <template #default="{ row }">{{ row.created_at || '—' }}</template>
            </el-table-column>
            <el-table-column label="下单时长" min-width="80" align="center">
              <template #default="{ row }">
                <span class="overdue-days">{{ row.order_days }}天</span>
              </template>
            </el-table-column>
            <el-table-column prop="shipping_status_text" label="发货状态" min-width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.shipping_status === 'virtual' ? 'info' : 'warning'" size="small">{{ row.shipping_status_text }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="produce_status_text" label="生产状态" min-width="90" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="{ unproduce: 'warning', producing: 'primary', produced: 'success' }[row.produce_status] || 'info'"
                  size="small"
                >{{ row.produce_status_text }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="预警类型" min-width="110" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.produce_status !== 'produced'" type="danger" size="small" effect="plain">未生产</el-tag>
                <el-tag type="warning" size="small" effect="plain" style="margin-left: 4px">未发货</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_by_name" label="销售员" min-width="80" align="center" v-if="isBoss" />
            <el-table-column label="操作" min-width="75" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click.stop="goOrder(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
defineOptions({ name: 'WarningCenter' })
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Warning, Van, User } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { getOverdueWarnings } from '@/api/warning'

const router = useRouter()
const userStore = useUserStore()
const isBoss = computed(() => userStore.isBoss)

const loading = ref(false)
const data = ref({ total_unproduced: 0, total_unsent: 0, sales_count: 0, overdue_days: 7, groups: [] })
const groups = computed(() => data.value.groups || [])
const days = ref(null)

// 表格自适应：el-table 仅监听 window resize，不监听容器自身变化；
// 用 ResizeObserver 监听卡片容器尺寸变化（含窗口缩放、布局变动），强制重新布局避免横向滚动条
const tableRef = ref(null)
const cardRef = ref(null)
let resizeObserver = null
function relayout() {
  nextTick(() => {
    const t = tableRef.value
    const arr = Array.isArray(t) ? t : (t ? [t] : [])
    arr.forEach(el => el && el.doLayout && el.doLayout())
  })
}
watch(groups, relayout)

async function fetchWarnings() {
  loading.value = true
  try {
    const params = {}
    if (days.value !== null && days.value !== undefined) params.days = days.value
    const res = await getOverdueWarnings(params)
    data.value = res
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function goOrder(row) {
  // 跳到订单列表并按平台订单号检索（订单列表支持 route.query.keyword 预置筛选）
  router.push({ path: '/orders', query: { keyword: row.platform_order_no } })
}

function goOrders() {
  router.push('/orders')
}

onMounted(() => {
  fetchWarnings()
  nextTick(() => {
    const el = cardRef.value && (cardRef.value.$el || cardRef.value)
    if (el && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => relayout())
      resizeObserver.observe(el)
    }
  })
})

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
})
</script>

<style scoped>
.warning-center {
  padding: 16px;
}

.stat-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border-radius: 8px;
  padding: 18px 20px;
  border: 1px solid #ebeef5;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-card.unproduced .stat-icon {
  background: linear-gradient(135deg, #f56c6c, #f78989);
}

.stat-card.unsent .stat-icon {
  background: linear-gradient(135deg, #e6a23c, #f0b95e);
}

.stat-card.sales .stat-icon {
  background: linear-gradient(135deg, #409eff, #79bbff);
}

.stat-num {
  font-size: 30px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.list-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sales-group {
  margin-bottom: 16px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 6px 6px 0 0;
}

.group-name {
  font-weight: 600;
  color: #303133;
}

.group-table {
  border-radius: 0 0 6px 6px;
}

.group-table :deep(.el-table__row) {
  cursor: pointer;
}

.overdue-days {
  color: #f56c6c;
  font-weight: 700;
}

.empty-tip {
  padding: 20px 0;
}
</style>
