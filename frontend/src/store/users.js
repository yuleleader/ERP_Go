import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUsers, updateUser, deleteUser } from '@/api/user'
import { register } from '@/api/auth'

export const useUsersStore = defineStore('users', () => {
  const users = ref([])
  const loading = ref(false)

  // 获取用户列表（支持 keyword 模糊搜索 / role 角色筛选，可组合）
  async function fetchUsers(params = {}) {
    loading.value = true
    try {
      users.value = await getUsers(params)
    } catch (error) {
      console.error('获取用户列表失败', error)
    } finally {
      loading.value = false
    }
  }

  // 创建用户
  async function createUser(userData) {
    try {
      await register(userData)
      await fetchUsers()
    } catch (error) {
      throw error
    }
  }

  // 更新用户
  async function updateUserInfo(userId, userData) {
    try {
      await updateUser(userId, userData)
      await fetchUsers()
    } catch (error) {
      throw error
    }
  }

  // 删除用户
  async function deleteUserInfo(userId) {
    try {
      await deleteUser(userId)
      await fetchUsers()
    } catch (error) {
      throw error
    }
  }

  return {
    users,
    loading,
    fetchUsers,
    createUser,
    updateUserInfo,
    deleteUserInfo
  }
})