import request from '@/utils/request'

/**
 * 获取订单列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 订单列表数据
 */
export function getOrders(params) {
  return request({
    url: '/orders/',
    method: 'get',
    params
  })
}

/**
 * 获取订单详情
 * @param {string} orderId - 订单ID
 * @returns {Promise} 订单详情数据
 */
export function getOrder(orderId) {
  return request({
    url: `/orders/${orderId}`,
    method: 'get'
  })
}

/**
 * 创建订单
 * @param {Object} data - 订单数据
 * @returns {Promise} 创建结果
 */
export function createOrder(data) {
  return request({
    url: '/orders/',
    method: 'post',
    data
  })
}

/**
 * 更新订单
 * @param {string} orderId - 订单ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export function updateOrder(orderId, data) {
  return request({
    url: `/orders/${orderId}`,
    method: 'put',
    data
  })
}

/**
 * 删除订单
 * @param {string} orderId - 订单ID
 * @param {string} password - 密码验证
 * @returns {Promise} 删除结果
 */
export function deleteOrder(orderId, password) {
  return request({
    url: `/orders/${orderId}`,
    method: 'delete',
    data: { password }
  })
}

/**
 * 生成订单预览
 * @param {string} shopId - 网店ID
 * @returns {Promise} 预览数据
 */
export function generateOrderPreview(shopId) {
  return request({
    url: '/orders/generate-preview',
    method: 'get',
    params: { shop_id: shopId },
    responseType: 'blob'
  })
}
