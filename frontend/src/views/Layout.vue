<template>
  <el-container class="layout-container" :class="{ 'fullscreen-dashboard': isFullscreenDashboard }">
    <el-aside v-if="!isFullscreenDashboard" width="200px" class="aside">
      <div class="logo">
        <h3>电商管理系统</h3>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="menu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409EFF"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/smart-dashboard" v-if="userStore.isBoss">
          <span>智慧大屏</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item index="/orders" v-if="userStore.role !== 'factory' && userStore.role !== 'shipping'">
          <span>订单管理</span>
        </el-menu-item>
        <el-menu-item v-if="menuGroups['basic-info'].groups.some((g) => g.items.length)" index="group:basic-info">
          <span>基础信息</span>
          <el-icon class="group-arrow"><ArrowRight /></el-icon>
        </el-menu-item>
        <el-menu-item v-if="menuGroups['statistics'].groups.some((g) => g.items.length)" index="group:statistics">
          <span>数据统计</span>
          <el-icon class="group-arrow"><ArrowRight /></el-icon>
        </el-menu-item>
        <el-menu-item v-if="menuGroups['finance'].groups.some((g) => g.items.length)" index="group:finance">
          <span>财务模块</span>
          <el-icon class="group-arrow"><ArrowRight /></el-icon>
        </el-menu-item>
        <el-menu-item v-if="menuGroups['system'].groups.some((g) => g.items.length)" index="group:system">
          <span>系统设置</span>
          <el-icon class="group-arrow"><ArrowRight /></el-icon>
        </el-menu-item>
      </el-menu>
      
      <div class="exchange-wrapper">
        <ExchangeCalculator />
      </div>
    </el-aside>

    <el-container class="main-container">
      <el-header v-if="!isFullscreenDashboard" class="header">
        <div class="header-left">
          <span class="page-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <!-- 站内信图标 -->
          <div class="notification-icon-wrapper" @click="goToNotifications">
            <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="notification-dot">
              <el-icon class="notification-icon"><Bell /></el-icon>
            </el-badge>
          </div>
          
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              {{ userStore.userInfo?.real_name || userStore.username }}
              <el-tag size="small" type="info">{{ roleName }}</el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- MDI 多标签栏 -->
      <div v-if="!isFullscreenDashboard" class="tabs-bar">
        <div class="tabs-scroll">
          <div
            v-for="tab in tabs"
            :key="tab.path"
            class="tab-item"
            :class="{ active: tab.path === route.path }"
            @click="switchTab(tab)"
          >
            <span class="tab-title">{{ tab.title }}</span>
            <el-icon v-if="!tab.affix" class="tab-close" @click.stop="closeTab(tab)"><Close /></el-icon>
          </div>
        </div>
      </div>

      <el-main class="main" :class="{ 'fullscreen-main': isFullscreenDashboard }">
        <router-view v-slot="{ Component }">
          <keep-alive :include="cachedViews">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px">
    <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules">
      <el-form-item label="原密码" prop="oldPassword">
        <el-input v-model="passwordForm.oldPassword" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="newPassword">
        <el-input v-model="passwordForm.newPassword" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="passwordDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleChangePassword">确定</el-button>
    </template>
  </el-dialog>

  <SubMenuDrawer
    v-model:visible="drawerVisible"
    :title="activeGroup.title"
    :groups="activeGroup.groups"
    :sidebar-width="200"
    width="720"
  />
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'
import ExchangeCalculator from '@/modules/Common/components/ExchangeCalculator.vue'
import SubMenuDrawer from '@/components/SubMenuDrawer.vue'
import { getUnreadCount } from '@/api/notification'
import { Bell, ArrowRight, Close } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

// 未读消息数量
const unreadCount = ref(0)
let refreshInterval = null

// 获取未读消息数量
async function fetchUnreadCount() {
  try {
    const response = await getUnreadCount()
    unreadCount.value = response.unread_count || 0
  } catch (error) {
    console.error('获取未读消息数量失败:', error)
  }
}

// 刷新未读消息数量
function refreshUnread() {
  if (userStore.token) {
    fetchUnreadCount()
  }
}

// 跳转到站内信页面
function goToNotifications() {
  router.push('/notifications')
}

// 在组件挂载时获取用户信息
onMounted(async () => {
  if (userStore.token) {
    loading.value = true
    try {
      await userStore.fetchUserInfo()
      // 恢复历史标签（角色已加载，可做权限过滤）
      initTabs()
      // 获取未读消息数量
      await fetchUnreadCount()
      // 设置定时刷新（每分钟）
      refreshInterval = setInterval(refreshUnread, 60000)
    } finally {
      loading.value = false
    }
  }
})

// 组件卸载时清理
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

const pageTitle = computed(() => route.meta.title || '')
const isFullscreenDashboard = computed(() => route.name === 'SmartDashboard')

// ========== MDI 多标签 ==========
// 打开功能页自动生成标签；点标签切换；点叉关闭；刷新后从 sessionStorage 恢复
const TABS_KEY = 'mdi_tabs'
const HOME_TAB = { path: '/dashboard', name: 'Dashboard', title: '工作台', affix: true }

const tabs = ref([])
const cachedViews = ref([])

function syncCachedViews() {
  cachedViews.value = tabs.value.filter((t) => t.name).map((t) => t.name)
}

function persistTabs() {
  try {
    sessionStorage.setItem(TABS_KEY, JSON.stringify(tabs.value))
  } catch (e) {
    /* 忽略存储异常 */
  }
}

// 解析路由 meta（含父级合并），用于标题与角色过滤
function routeMetaFor(path) {
  try {
    return router.resolve(path).meta || {}
  } catch (e) {
    return {}
  }
}

function isTabAllowed(path) {
  const meta = routeMetaFor(path)
  if (meta.roles && userStore.role && !meta.roles.includes(userStore.role)) return false
  return true
}

// 将当前路由同步进标签栏（不存在则新建，已存在则更新 query）
function syncCurrentTab() {
  if (route.name === 'SmartDashboard' || route.path === '/smart-dashboard') return
  const meta = route.meta || {}
  if (!meta.title) return
  const existing = tabs.value.find((t) => t.path === route.path)
  if (existing) {
    existing.query = { ...route.query }
  } else {
    tabs.value.push({
      path: route.path,
      name: route.name,
      query: { ...route.query },
      title: meta.title,
      affix: false
    })
  }
  syncCachedViews()
  persistTabs()
}

// 刷新恢复历史标签
function initTabs() {
  let saved = []
  try {
    saved = JSON.parse(sessionStorage.getItem(TABS_KEY) || '[]')
  } catch (e) {
    saved = []
  }
  tabs.value = [{ ...HOME_TAB }]
  for (const t of saved) {
    if (!t || !t.path || t.path === HOME_TAB.path) continue
    if (!t.title) {
      const meta = routeMetaFor(t.path)
      t.title = meta.title || ''
    }
    if (!t.title) continue
    if (!isTabAllowed(t.path)) continue
    if (tabs.value.some((x) => x.path === t.path)) continue
    tabs.value.push({ path: t.path, name: t.name, query: t.query || {}, title: t.title, affix: false })
  }
  syncCurrentTab()
  syncCachedViews()
  persistTabs()
}

// 切换标签
function switchTab(tab) {
  if (tab.path === route.path) return
  router.push({ path: tab.path, query: tab.query || {} })
}

// 关闭标签：若关闭的是当前激活标签，自动切到相邻标签
function closeTab(tab) {
  const idx = tabs.value.findIndex((t) => t.path === tab.path)
  if (idx === -1) return
  tabs.value.splice(idx, 1)
  syncCachedViews()
  if (route.path === tab.path) {
    const next = tabs.value[idx] || tabs.value[idx - 1]
    if (next) router.push({ path: next.path, query: next.query || {} })
  }
  persistTabs()
}

// 路由变化 → 自动建标签/更新标签（统一入口：菜单、抽屉、站内信跳转、URL 直达均生效）
watch(
  () => route.fullPath,
  () => syncCurrentTab(),
  { immediate: true }
)

// ========== 抽屉式二级菜单 ==========
// 一级菜单点击后从右侧弹出抽屉展示二级菜单，点击二级菜单跳转到对应功能页面
const menuGroups = computed(() => {
  const isBoss = userStore.isBoss
  const isSales = userStore.isSales
  const pick = (arr) => arr.filter((item) => item.show !== false)

  return {
    'basic-info': {
      title: '基础信息',
      groups: [
        {
          title: '商品资料',
          items: pick([
            { label: '商品管理', path: '/products', desc: '商品资料与规格（所有人员可查看）', show: true },
            { label: '类别管理', path: '/categories', desc: '两级类别与编码维护（操作按数据权限）', show: true },
            { label: '品牌管理', path: '/brands', desc: '品牌编码与名称维护（操作按数据权限）', show: true }
          ])
        },
        {
          title: '店铺物流',
          items: pick([
            { label: '网店信息', path: '/shops', desc: '管理店铺账号与归属', show: isBoss || isSales },
            { label: '物流管理', path: '/logistics', desc: '维护物流商与运费信息', show: isBoss }
          ])
        }
      ].filter((g) => g.items.length)
    },
    statistics: {
      title: '数据统计',
      groups: [
        {
          title: '数据概览',
          items: pick([
            { label: '数据总览', path: '/statistics', desc: '核心指标卡片与销售趋势图', show: true }
          ])
        },
        {
          title: '销售分析',
          items: pick([
            { label: '销售统计', path: '/sales-statistics', desc: '人员/类别/品牌/商品销售汇总', show: isBoss },
            { label: '毛利分析', path: '/gross-profit-analysis', desc: '按下单/发货时间核算毛利', show: isBoss },
            { label: '网店销售统计', path: '/shop-sales-statistics', desc: '按网店汇总销售与退货', show: isBoss },
            { label: '退款订单', path: '/refund-orders', desc: '已退货/退款订单明细', show: isBoss },
            { label: '退款率分析', path: '/refund-rate-analysis', desc: '按网店统计退款率报表', show: isBoss }
          ])
        },
        {
          title: '预警管理',
          items: pick([
            { label: '预警中心', path: '/warnings', desc: '超期未生产/未发货订单自动提醒', show: isBoss || isSales }
          ])
        },
        {
          title: '提成核算',
          items: pick([
            { label: '销售提成统计', path: '/commission-statistics', desc: '按发货时间核算销售提成', show: true }
          ])
        }
      ].filter((g) => g.items.length)
    },
    finance: {
      title: '财务模块',
      groups: [
        {
          title: '财务结算',
          items: pick([
            { label: '工资结算', path: '/salary-settlement', desc: '销售提成核算与发放', show: isBoss },
            { label: '账户提现', path: '/account-withdrawal', desc: '提现申请与审批记录', show: isBoss || isSales }
          ])
        },
        {
          title: '费用统计',
          items: pick([
            { label: '运费统计', path: '/freight-statistics', desc: '按订单时间段统计运费', show: isBoss }
          ])
        },
        {
          title: '非交易收支',
          items: pick([
            { label: '账务代码', path: '/accounting-codes', desc: '非交易收入/支出类型字典维护', show: isBoss },
            { label: '收支录入', path: '/non-trade-transactions', desc: '录入非交易收入/支出（每人维护自己的数据）', show: isBoss || isSales },
            { label: '收支统计', path: '/non-trade-summary', desc: '按账务代码/人员汇总非交易收支', show: isBoss }
          ])
        }
      ].filter((g) => g.items.length)
    },
    system: {
      title: '系统设置',
      groups: [
        {
          title: '系统运维',
          items: pick([
            { label: '系统参数', path: '/settings', desc: '提成比例、临时图片保留等配置', show: isBoss },
            { label: '日志清理', path: '/data-cleanup', desc: '日志与站内信清理配置及记录', show: isBoss },
            { label: '日志管理', path: '/logs', desc: '操作日志与登录日志查询', show: isBoss },
            { label: '数据导入', path: '/order-imports', desc: 'Excel 批量导入订单（临时表审核后合并）', show: isBoss || isSales }
          ])
        },
        {
          title: '账号权限',
          items: pick([
            { label: '用户管理', path: '/users', desc: '账号、角色与权限维护', show: isBoss }
          ])
        },
        {
          title: '消息通讯',
          items: pick([
            { label: '站内信管理', path: '/notifications', desc: '消息收发与已读状态', show: true }
          ])
        },
        {
          title: '关于本系统',
          items: pick([
            { label: '系统信息', path: '/system-info', desc: '版本、运行环境与数据概况', show: isBoss }
          ])
        }
      ].filter((g) => g.items.length)
    }
  }
})

const drawerVisible = ref(false)
const activeGroupKey = ref('basic-info')
const activeGroup = computed(() => menuGroups.value[activeGroupKey.value] || { title: '', items: [] })

// 当前路由属于哪个分组（用于侧边栏一级菜单高亮）
const activeMenu = computed(() => {
  for (const [key, group] of Object.entries(menuGroups.value)) {
    if (group.groups.some((g) => g.items.some((item) => item.path === route.path))) {
      return `group:${key}`
    }
  }
  return route.path
})

function handleMenuSelect(index) {
  if (index.startsWith('group:')) {
    activeGroupKey.value = index.slice(6)
    drawerVisible.value = true
    return
  }
  if (index !== route.path) router.push(index)
}

const roleNames = {
  boss: '老板端',
  sales: '销售端',
  factory: '工厂端',
  shipping: '发货端'
}
const roleName = computed(() => roleNames[userStore.role] || '')

// 计算是否已加载用户信息
const userInfoLoaded = computed(() => userStore.userInfo !== null)

// 计算是否显示加载中
const showLoading = computed(() => loading.value && userStore.token)

const passwordDialogVisible = ref(false)
const passwordFormRef = ref(null)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: ''
})
const passwordRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return
  try {
    await passwordFormRef.value.validate()
    await userStore.changePasswordAction(passwordForm.oldPassword, passwordForm.newPassword)
    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
  } catch (error) {
    if (error?.response) {
      ElMessage.error(error.response?.data?.detail || '修改失败')
    }
    // 表单验证错误不弹错误提示
  }
}

function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'password') {
    passwordDialogVisible.value = true
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.main-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.aside {
  background-color: #001529;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #002140;
}

.logo h3 {
  color: #fff;
  font-size: 18px;
  margin: 0;
}

.menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  height: 60px;
  flex-shrink: 0;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.main {
  background-color: #f0f2f5;
  padding: 20px;
  flex: 1;
  overflow: auto;
  min-height: calc(100vh - 100px);
}

.main.fullscreen-main {
  padding: 0;
  background-color: transparent;
  overflow: hidden;
}

.fullscreen-dashboard .main-container {
  height: 100vh;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.notification-icon-wrapper {
  position: relative;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.notification-icon-wrapper:hover {
  background-color: #f0f2f5;
}

.notification-icon {
  font-size: 20px;
  color: #666;
}

.notification-dot {
  --el-badge-dot-size: 8px;
  --el-badge-font-size: 10px;
}

.exchange-wrapper {
  padding: 10px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: auto;
}

.group-arrow {
  margin-left: auto;
  font-size: 12px;
  opacity: 0.45;
}

/* ===== MDI 多标签栏 ===== */
.tabs-bar {
  height: 40px;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 5;
}

.tabs-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
}

.tabs-scroll::-webkit-scrollbar {
  display: none;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.15s;
  user-select: none;
}

.tab-item:hover {
  background: #ecf5ff;
  color: #409eff;
}

.tab-item.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.tab-title {
  line-height: 1;
}

.tab-close {
  font-size: 12px;
  opacity: 0.65;
  border-radius: 50%;
}

.tab-close:hover {
  opacity: 1;
  color: #f56c6c;
}
</style>
