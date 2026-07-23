/**
 * 物流管理业务逻辑层
 */

import { logisticsApi } from '@/api'

/**
 * 获取物流公司列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 物流公司列表数据
 */
export async function fetchLogisticsList(params) {
  try {
    const response = await logisticsApi.getLogisticsCompanies(params)
    return response
  } catch (error) {
    console.error('获取物流公司列表失败:', error)
    throw error
  }
}

/**
 * 创建物流公司
 * @param {Object} data - 物流公司数据
 * @returns {Promise} 创建结果
 */
export async function createLogistics(data) {
  try {
    const response = await logisticsApi.createLogisticsCompany(data)
    return response
  } catch (error) {
    console.error('创建物流公司失败:', error)
    throw error
  }
}

/**
 * 更新物流公司
 * @param {number} companyId - 物流公司ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export async function updateLogistics(companyId, data) {
  try {
    const response = await logisticsApi.updateLogisticsCompany(companyId, data)
    return response
  } catch (error) {
    console.error('更新物流公司失败:', error)
    throw error
  }
}

/**
 * 删除物流公司
 * @param {number} companyId - 物流公司ID
 * @returns {Promise} 删除结果
 */
export async function removeLogistics(companyId) {
  try {
    const response = await logisticsApi.deleteLogisticsCompany(companyId)
    return response
  } catch (error) {
    console.error('删除物流公司失败:', error)
    throw error
  }
}