import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUsers, updateUser, deleteUser } from '@/api/user'
import { register } from '@/api/auth'

export const useUsersStore = defineStore('users', () => {
  const users = ref([])
  const loading = ref(false)

  // 获取用户列表
  async function fetchUsers() {
    loading.value = true
    try {
      users.value = await getUsers()
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