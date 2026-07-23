/**
 * 订单管理业务逻辑层
 * 负责订单相关的数据处理、计算等业务逻辑
 */

import { orderApi } from '@/api'

/**
 * 订单状态映射
 */
const ORDER_STATUS_MAP = {
  pending: '待发货',
  shipped: '已发货',
  virtual: '虚拟发货'
}

/**
 * 订单状态类型映射
 */
const ORDER_STATUS_TYPE_MAP = {
  pending: 'warning',
  shipped: 'success',
  virtual: 'info'
}

/**
 * 获取订单状态文本
 * @param {string} status - 订单状态
 * @returns {string} 状态文本
 */
export function getOrderStatusText(status) {
  return ORDER_STATUS_MAP[status] || status
}

/**
 * 获取订单状态类型
 * @param {string} status - 订单状态
 * @returns {string} 状态类型
 */
export function getOrderStatusType(status) {
  return ORDER_STATUS_TYPE_MAP[status] || 'info'
}

/**
 * 计算提成金额
 * @param {number} salesAmount - 销售金额
 * @param {number} commissionRate - 提成比例
 * @returns {number} 提成金额
 */
export function calculateCommission(salesAmount, commissionRate) {
  if (!salesAmount || !commissionRate) return 0
  return (parseFloat(salesAmount) * commissionRate) / 100
}

/**
 * 获取订单列表
 * @param {Object} params - 查询参数
 * @returns {Promise} 订单列表数据
 */
export async function fetchOrderList(params) {
  try {
    const response = await orderApi.getOrders(params)
    return response
  } catch (error) {
    console.error('获取订单列表失败:', error)
    throw error
  }
}

/**
 * 获取订单详情
 * @param {string} orderId - 订单ID
 * @returns {Promise} 订单详情数据
 */
export async function fetchOrderDetail(orderId) {
  try {
    const response = await orderApi.getOrder(orderId)
    return response
  } catch (error) {
    console.error('获取订单详情失败:', error)
    throw error
  }
}

/**
 * 创建订单
 * @param {Object} data - 订单数据
 * @returns {Promise} 创建结果
 */
export async function createOrder(data) {
  try {
    // 自动计算提成金额
    if (data.sales_amount && data.commission_rate) {
      data.commission_amount = calculateCommission(
        data.sales_amount,
        data.commission_rate
      )
    }
    
    const response = await orderApi.createOrder(data)
    return response
  } catch (error) {
    console.error('创建订单失败:', error)
    throw error
  }
}

/**
 * 更新订单
 * @param {string} orderId - 订单ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export async function updateOrder(orderId, data) {
  try {
    // 如果更新了销售金额或提成比例，重新计算提成
    if (data.sales_amount || data.commission_rate) {
      const order = await fetchOrderDetail(orderId)
      const salesAmount = data.sales_amount || order.sales_amount
      const commissionRate = data.commission_rate || order.commission_rate
      data.commission_amount = calculateCommission(salesAmount, commissionRate)
    }
    
    const response = await orderApi.updateOrder(orderId, data)
    return response
  } catch (error) {
    console.error('更新订单失败:', error)
    throw error
  }
}

/**
 * 删除订单
 * @param {string} orderId - 订单ID
 * @param {string} password - 密码验证
 * @returns {Promise} 删除结果
 */
export async function removeOrder(orderId, password) {
  try {
    const response = await orderApi.deleteOrder(orderId, password)
    return response
  } catch (error) {
    console.error('删除订单失败:', error)
    throw error
  }
}

/**
 * 生成订单预览
 * @param {string} shopId - 网店ID
 * @returns {Promise} 预览数据
 */
export async function generatePreview(shopId) {
  try {
    const response = await orderApi.generateOrderPreview(shopId)
    return response
  } catch (error) {
    console.error('生成订单预览失败:', error)
    throw error
  }
}