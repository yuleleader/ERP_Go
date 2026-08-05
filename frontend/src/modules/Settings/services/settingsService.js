/**
 * 系统设置业务逻辑层
 */

import { userApi } from '@/api'

/**
 * 获取系统设置
 * @param {string} key - 设置键
 * @returns {Promise} 设置值
 */
export async function getSetting(key) {
  try {
    const response = await userApi.getSystemSetting(key)
    return response
  } catch (error) {
    console.error('获取系统设置失败:', error)
    throw error
  }
}

/**
 * 更新系统设置
 * @param {string} key - 设置键
 * @param {string} value - 设置值
 * @returns {Promise} 更新结果
 */
export async function updateSetting(key, value) {
  try {
    const response = await userApi.updateSystemSetting(key, value)
    return response
  } catch (error) {
    console.error('更新系统设置失败:', error)
    throw error
  }
}

/**
 * 重置用户密码
 * @param {number} userId - 用户ID
 * @param {string} newPassword - 新密码
 * @returns {Promise} 重置结果
 */
export async function resetUserPassword(userId, newPassword) {
  try {
    const response = await userApi.resetPassword(userId, { new_password: newPassword })
    return response
  } catch (error) {
    console.error('重置用户密码失败:', error)
    throw error
  }
}