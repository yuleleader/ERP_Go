/**
 * 图片管理业务逻辑层
 */

import { imageApi } from '@/api'

/**
 * 上传临时图片
 * @param {FormData} formData - 图片数据
 * @returns {Promise} 上传结果
 */
export async function uploadTempImage(formData) {
  try {
    const response = await imageApi.uploadTemp(formData)
    return response
  } catch (error) {
    console.error('上传临时图片失败:', error)
    throw error
  }
}

/**
 * 直接上传图片
 * @param {string} orderId - 订单ID
 * @param {FormData} formData - 图片数据
 * @returns {Promise} 上传结果
 */
export async function uploadDirectImage(orderId, formData) {
  try {
    const response = await imageApi.uploadDirect(orderId, formData)
    return response
  } catch (error) {
    console.error('直接上传图片失败:', error)
    throw error
  }
}

/**
 * 迁移临时图片
 * @param {string} tempId - 临时图片ID
 * @param {string} orderId - 订单ID
 * @returns {Promise} 迁移结果
 */
export async function migrateImage(tempId, orderId) {
  try {
    const response = await imageApi.migrate(tempId, orderId)
    return response
  } catch (error) {
    console.error('迁移图片失败:', error)
    throw error
  }
}

/**
 * 获取订单图片列表
 * @param {string} orderId - 订单ID
 * @returns {Promise} 图片列表数据
 */
export async function fetchOrderImages(orderId) {
  try {
    const response = await imageApi.listImages(orderId)
    return response
  } catch (error) {
    console.error('获取订单图片列表失败:', error)
    throw error
  }
}

/**
 * 删除图片
 * @param {number} imageId - 图片ID
 * @returns {Promise} 删除结果
 */
export async function removeImage(imageId) {
  try {
    const response = await imageApi.deleteImage(imageId)
    return response
  } catch (error) {
    console.error('删除图片失败:', error)
    throw error
  }
}

/**
 * 设置主图
 * @param {number} imageId - 图片ID
 * @returns {Promise} 设置结果
 */
export async function setMainImage(imageId) {
  try {
    const response = await imageApi.setMain(imageId)
    return response
  } catch (error) {
    console.error('设置主图失败:', error)
    throw error
  }
}

/**
 * 清理临时图片
 * @returns {Promise} 清理结果
 */
export async function cleanTempImages() {
  try {
    const response = await imageApi.cleanTemp()
    return response
  } catch (error) {
    console.error('清理临时图片失败:', error)
    throw error
  }
}