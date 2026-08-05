/**
 * 数据统计业务逻辑层
 */

import { statisticsApi } from '@/api'

/**
 * 获取综合统计概览
 * @param {Object} params - 查询参数
 * @returns {Promise} 统计数据
 */
export async function fetchOverview(params) {
  try {
    const response = await statisticsApi.getOverview(params)
    return response
  } catch (error) {
    console.error('获取综合统计概览失败:', error)
    throw error
  }
}

/**
 * 获取销售总金额统计
 * @param {Object} params - 查询参数
 * @returns {Promise} 销售统计数据
 */
export async function fetchSalesTotal(params) {
  try {
    const response = await statisticsApi.getSalesTotal(params)
    return response
  } catch (error) {
    console.error('获取销售总金额统计失败:', error)
    throw error
  }
}

/**
 * 获取理论应得提成
 * @param {Object} params - 查询参数
 * @returns {Promise} 提成统计数据
 */
export async function fetchCommissionTheoretical(params) {
  try {
    const response = await statisticsApi.getCommissionTheoretical(params)
    return response
  } catch (error) {
    console.error('获取理论应得提成失败:', error)
    throw error
  }
}

/**
 * 获取实际应得提成
 * @param {Object} params - 查询参数
 * @returns {Promise} 提成统计数据
 */
export async function fetchCommissionActual(params) {
  try {
    const response = await statisticsApi.getCommissionActual(params)
    return response
  } catch (error) {
    console.error('获取实际应得提成失败:', error)
    throw error
  }
}

/**
 * 按用户统计提成
 * @param {Object} params - 查询参数
 * @returns {Promise} 用户提成统计数据
 */
export async function fetchCommissionByUser(params) {
  try {
    const response = await statisticsApi.getCommissionByUser(params)
    return response
  } catch (error) {
    console.error('获取用户提成统计失败:', error)
    throw error
  }
}

/**
 * 获取平均发货时长统计
 * @param {Object} params - 查询参数
 * @returns {Promise} 发货时长统计数据
 */
export async function fetchAvgShippingTime(params) {
  try {
    const response = await statisticsApi.getAvgShippingTime(params)
    return response
  } catch (error) {
    console.error('获取平均发货时长统计失败:', error)
    throw error
  }
}