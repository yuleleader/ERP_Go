/**
 * 用户管理业务逻辑层
 */

import { userApi } from '@/api'

/**
 * 获取用户列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 用户列表数据
 */
export async function fetchUserList(params) {
  try {
    const response = await userApi.getUsers(params)
    return response
  } catch (error) {
    console.error('获取用户列表失败:', error)
    throw error
  }
}

/**
 * 创建用户
 * @param {Object} data - 用户数据
 * @returns {Promise} 创建结果
 */
export async function createUser(data) {
  try {
    const response = await userApi.createUser(data)
    return response
  } catch (error) {
    console.error('创建用户失败:', error)
    throw error
  }
}

/**
 * 更新用户
 * @param {number} userId - 用户ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export async function updateUser(userId, data) {
  try {
    const response = await userApi.updateUser(userId, data)
    return response
  } catch (error) {
    console.error('更新用户失败:', error)
    throw error
  }
}

/**
 * 删除用户
 * @param {number} userId - 用户ID
 * @returns {Promise} 删除结果
 */
export async function removeUser(userId) {
  try {
    const response = await userApi.deleteUser(userId)
    return response
  } catch (error) {
    console.error('删除用户失败:', error)
    throw error
  }
}