import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, getCurrentUser, register, changePassword, resetPassword } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => userInfo.value?.role || '')
  const username = computed(() => userInfo.value?.username || '')
  const isBoss = computed(() => role.value === 'boss')
  const isSales = computed(() => role.value === 'sales')
  const isFactory = computed(() => role.value === 'factory')
  const isShipping = computed(() => role.value === 'shipping')

  async function loginAction(credentials) {
    const res = await login(credentials)
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    await fetchUserInfo()
    return res
  }

  async function fetchUserInfo() {
    if (!token.value) return
    try {
      const res = await getCurrentUser()
      userInfo.value = res
    } catch (e) {
      logout()
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  async function registerAction(userData) {
    return await register(userData)
  }

  async function changePasswordAction(oldPassword, newPassword) {
    return await changePassword(oldPassword, newPassword)
  }

  async function resetPasswordAction(userId) {
    return await resetPassword(userId)
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    role,
    username,
    isBoss,
    isSales,
    isFactory,
    isShipping,
    loginAction,
    fetchUserInfo,
    logout,
    registerAction,
    changePasswordAction,
    resetPasswordAction
  }
})
