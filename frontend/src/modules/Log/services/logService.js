/**
 * 日志管理业务逻辑层
 */

import { logApi } from '@/api'

/**
 * 获取操作日志
 * @param {Object} params - 查询参数
 * @returns {Promise} 日志列表数据
 */
export async function fetchOperationLogs(params) {
  try {
    const response = await logApi.getOperationLogs(params)
    return response
  } catch (error) {
    console.error('获取操作日志失败:', error)
    throw error
  }
}

/**
 * 获取登录日志
 * @param {Object} params - 查询参数
 * @returns {Promise} 日志列表数据
 */
export async function fetchLoginLogs(params) {
  try {
    const response = await logApi.getLoginLogs(params)
    return response
  } catch (error) {
    console.error('获取登录日志失败:', error)
    throw error
  }
}

/**
 * 获取日志清理配置
 * @returns {Promise} 清理配置
 */
export async function fetchCleanupConfig() {
  try {
    const response = await logApi.getCleanupConfig()
    return response
  } catch (error) {
    console.error('获取日志清理配置失败:', error)
    throw error
  }
}

/**
 * 更新日志清理配置
 * @param {Object} data - 配置数据
 * @returns {Promise} 更新结果
 */
export async function updateCleanupConfig(data) {
  try {
    const response = await logApi.updateCleanupConfig(data)
    return response
  } catch (error) {
    console.error('更新日志清理配置失败:', error)
    throw error
  }
}

/**
 * 预览清理效果
 * @param {Object} data - 清理参数
 * @returns {Promise} 预览结果
 */
export async function previewCleanup(data) {
  try {
    const response = await logApi.previewCleanup(data)
    return response
  } catch (error) {
    console.error('预览清理效果失败:', error)
    throw error
  }
}

/**
 * 执行日志清理
 * @param {Object} data - 清理参数
 * @returns {Promise} 清理结果
 */
export async function executeCleanup(data) {
  try {
    const response = await logApi.executeCleanup(data)
    return response
  } catch (error) {
    console.error('执行日志清理失败:', error)
    throw error
  }
}

/**
 * 获取清理记录
 * @param {Object} params - 查询参数
 * @returns {Promise} 清理记录列表
 */
export async function fetchCleanupRecords(params) {
  try {
    const response = await logApi.getCleanupRecords(params)
    return response
  } catch (error) {
    console.error('获取清理记录失败:', error)
    throw error
  }
}