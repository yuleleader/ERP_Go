/**
 * 商品管理业务逻辑层
 */

import { productApi } from '@/api'

/**
 * 获取商品列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 商品列表数据
 */
export async function fetchProductList(params) {
  try {
    const response = await productApi.getProducts(params)
    return response
  } catch (error) {
    console.error('获取商品列表失败:', error)
    throw error
  }
}

/**
 * 创建商品
 * @param {Object} data - 商品数据
 * @returns {Promise} 创建结果
 */
export async function createProduct(data) {
  try {
    const response = await productApi.createProduct(data)
    return response
  } catch (error) {
    console.error('创建商品失败:', error)
    throw error
  }
}

/**
 * 更新商品
 * @param {string} productCode - 商品编码
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export async function updateProduct(productCode, data) {
  try {
    const response = await productApi.updateProduct(productCode, data)
    return response
  } catch (error) {
    console.error('更新商品失败:', error)
    throw error
  }
}

/**
 * 删除商品
 * @param {string} productCode - 商品编码
 * @returns {Promise} 删除结果
 */
export async function removeProduct(productCode) {
  try {
    const response = await productApi.deleteProduct(productCode)
    return response
  } catch (error) {
    console.error('删除商品失败:', error)
    throw error
  }
}

/**
 * 批量删除商品
 * @param {Array<string>} productCodes - 商品编码数组
 * @returns {Promise} 删除结果
 */
export async function batchRemoveProducts(productCodes) {
  try {
    const response = await productApi.batchDeleteProducts({ product_codes: productCodes })
    return response
  } catch (error) {
    console.error('批量删除商品失败:', error)
    throw error
  }
}