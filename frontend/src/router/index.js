import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '工作台' }
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/modules/Order/views/Orders.vue'),
        meta: { title: '订单管理' }
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('@/views/Products.vue'),
        meta: { title: '商品管理', roles: ['boss'] }
      },
      {
        path: 'shops',
        name: 'Shops',
        component: () => import('@/views/Shops.vue'),
        meta: { title: '网店管理', roles: ['boss', 'sales'] }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { title: '用户管理', roles: ['boss'] }
      },
      {
        path: 'logistics',
        name: 'Logistics',
        component: () => import('@/views/Logistics.vue'),
        meta: { title: '物流管理', roles: ['boss'] }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '系统设置', roles: ['boss'] }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/Logs.vue'),
        meta: { title: '日志管理', roles: ['boss'] }
      },
      {
        path: 'images',
        name: 'Images',
        component: () => import('@/views/Images.vue'),
        meta: { title: '图片管理' }
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/Statistics.vue'),
        meta: { title: '数据统计' }
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/Notifications.vue'),
        meta: { title: '站内信' }
      },
      {
        path: 'smart-dashboard',
        name: 'SmartDashboard',
        component: () => import('@/views/SmartDashboard.vue'),
        meta: { title: '智慧大屏', roles: ['boss'] }
      },
      {
        path: 'salary-settlement',
        name: 'SalarySettlement',
        component: () => import('@/modules/Finance/views/CommissionSettlement.vue'),
        meta: { title: '工资结算', roles: ['boss'] }
      },
      {
        path: 'account-withdrawal',
        name: 'AccountWithdrawal',
        component: () => import('@/modules/Finance/views/AccountWithdrawal.vue'),
        meta: { title: '账户提现', roles: ['boss'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.token) {
    next('/login')
  } else if (to.path === '/login' && userStore.token) {
    next('/')
  } else if (to.meta.roles) {
    // 首次刷新/深链进入受限页面时，角色信息可能尚未加载；先补拉用户信息再判断权限
    if (userStore.token && !userStore.userInfo) {
      await userStore.fetchUserInfo()
    }
    if (!to.meta.roles.includes(userStore.role)) {
      next('/dashboard')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
