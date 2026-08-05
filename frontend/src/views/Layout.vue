<template>
  <el-container class="layout-container" :class="{ 'fullscreen-dashboard': isFullscreenDashboard }">
    <el-aside v-if="!isFullscreenDashboard" width="200px" class="aside">
      <div class="logo">
        <h3>电商管理系统</h3>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409EFF"
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
        <el-sub-menu index="basic-info" v-if="userStore.isBoss || userStore.isSales">
          <template #title>
            <span>基础信息</span>
          </template>
          <el-menu-item index="/products" v-if="userStore.isBoss">商品管理</el-menu-item>
          <el-menu-item index="/shops">网店信息</el-menu-item>
          <el-menu-item index="/users" v-if="userStore.isBoss">用户管理</el-menu-item>
          <el-menu-item index="/logistics" v-if="userStore.isBoss">物流管理</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/statistics">
          <span>数据统计</span>
        </el-menu-item>
        <el-sub-menu index="finance" v-if="userStore.isBoss || userStore.isSales">
          <template #title>
            <span>财务模块</span>
          </template>
          <el-menu-item index="/salary-settlement" v-if="userStore.isBoss">工资结算</el-menu-item>
          <el-menu-item index="/account-withdrawal">账户提现</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/settings" v-if="userStore.isBoss">
          <span>系统设置</span>
        </el-menu-item>
        <el-menu-item index="/logs" v-if="userStore.isBoss">
          <span>日志管理</span>
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

      <el-main class="main" :class="{ 'fullscreen-main': isFullscreenDashboard }">
        <router-view />
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
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'
import ExchangeCalculator from '@/modules/Common/components/ExchangeCalculator.vue'
import { getUnreadCount } from '@/api/notification'
import { Bell } from '@element-plus/icons-vue'

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

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta.title || '')
const isFullscreenDashboard = computed(() => route.name === 'SmartDashboard')

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
  min-height: calc(100vh - 60px);
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
</style>
