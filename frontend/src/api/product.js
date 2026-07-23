/**
 * 商品管理API接口
 * 提供商品的增删改查功能
 */
import request from '@/utils/request'

/**
 * 获取商品列表
 * @param {Object} params - 查询参数
 * @param {string} params.keyword - 搜索关键词（商品编码、商品名称）
 * @param {string} params.status - 商品状态（active/inactive）
 * @param {number} params.skip - 跳过记录数
 * @param {number} params.limit - 返回记录数
 * @returns {Promise} 商品列表
 */
export function getProducts(params = {}) {
  return request({
    url: '/products/',
    method: 'get',
    params
  })
}

/**
 * 获取商品详情
 * @param {string} productCode - 商品编码
 * @returns {Promise} 商品详情
 */
export function getProductDetail(productCode) {
  return request({
    url: `/products/${productCode}`,
    method: 'get'
  })
}

/**
 * 创建商品
 * @param {Object} data - 商品数据
 * @param {string} data.product_name - 商品名称（2-100字符）
 * @param {string} data.product_remark - 商品备注（最大500字符）
 * @returns {Promise} 创建结果
 */
export function createProduct(data) {
  return request({
    url: '/products/',
    method: 'post',
    data
  })
}

/**
 * 更新商品信息
 * @param {string} productCode - 商品编码
 * @param {Object} data - 更新数据
 * @param {string} data.product_name - 商品名称
 * @param {string} data.product_remark - 商品备注
 * @param {string} data.status - 商品状态
 * @returns {Promise} 更新结果
 */
export function updateProduct(productCode, data) {
  return request({
    url: `/products/${productCode}`,
    method: 'put',
    data
  })
}

/**
 * 删除商品
 * @param {string} productCode - 商品编码
 * @returns {Promise} 删除结果
 */
export function deleteProduct(productCode) {
  return request({
    url: `/products/${productCode}`,
    method: 'delete'
  })
}

/**
 * 批量删除商品
 * @param {Array<string>} productCodes - 商品编码列表
 * @returns {Promise} 批量删除结果
 */
export function batchDeleteProducts(productCodes) {
  return request({
    url: '/products/batch-delete',
    method: 'post',
    data: productCodes
  })
}

/**
 * 获取商品统计信息
 * @returns {Promise} 商品统计（总数、启用数、停用数）
 */
export function getProductCount() {
  return request({
    url: '/products/count/total',
    method: 'get'
  })
}