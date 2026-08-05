/**
 * 网店管理业务逻辑层
 */

import { shopApi } from '@/api'

/**
 * 获取网店列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 网店列表数据
 */
export async function fetchShopList(params) {
  try {
    const response = await shopApi.getShops(params)
    return response
  } catch (error) {
    console.error('获取网店列表失败:', error)
    throw error
  }
}

/**
 * 创建网店
 * @param {Object} data - 网店数据
 * @returns {Promise} 创建结果
 */
export async function createShop(data) {
  try {
    const response = await shopApi.createShop(data)
    return response
  } catch (error) {
    console.error('创建网店失败:', error)
    throw error
  }
}

/**
 * 更新网店
 * @param {number} shopId - 网店ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export async function updateShop(shopId, data) {
  try {
    const response = await shopApi.updateShop(shopId, data)
    return response
  } catch (error) {
    console.error('更新网店失败:', error)
    throw error
  }
}

/**
 * 删除网店
 * @param {number} shopId - 网店ID
 * @returns {Promise} 删除结果
 */
export async function removeShop(shopId) {
  try {
    const response = await shopApi.deleteShop(shopId)
    return response
  } catch (error) {
    console.error('删除网店失败:', error)
    throw error
  }
}