import request from '@/utils/request'

/**
 * 获取未发放提成列表
 * @param {string} month - 查询月份，格式 YYYY-MM
 * @returns {Promise} 未发放提成汇总数据
 */
export function getUnpaidCommission(month) {
  return request({
    url: '/commission-settlement/unpaid',
    method: 'get',
    params: { month }
  })
}

/**
 * 获取未发放提成订单详情
 * @param {string} month - 查询月份，格式 YYYY-MM
 * @param {string} username - 销售用户名（可选）
 * @returns {Promise} 未发放提成订单列表
 */
export function getUnpaidOrders(month, username) {
  return request({
    url: '/commission-settlement/unpaid/orders',
    method: 'get',
    params: { month, username }
  })
}

/**
 * 标记提成已发放
 * @param {string} month - 发放月份，格式 YYYY-MM
 * @param {string} username - 销售用户名（可选）
 * @returns {Promise} 发放结果
 */
export function payCommission(month, username) {
  return request({
    url: '/commission-settlement/pay',
    method: 'post',
    params: { month, username }
  })
}
