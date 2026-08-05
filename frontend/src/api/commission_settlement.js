import request from '@/utils/request'

/**
 * 获取未发放提成列表
 * @param {string} startDate - 结算开始日期，格式 YYYY-MM-DD
 * @param {string} endDate - 结算结束日期，格式 YYYY-MM-DD（含当天）
 * @returns {Promise} 未发放提成汇总数据
 */
export function getUnpaidCommission(startDate, endDate) {
  return request({
    url: '/commission-settlement/unpaid',
    method: 'get',
    params: { start_date: startDate, end_date: endDate }
  })
}

/**
 * 获取未发放提成订单详情
 * @param {string} startDate - 结算开始日期，格式 YYYY-MM-DD
 * @param {string} endDate - 结算结束日期，格式 YYYY-MM-DD（含当天）
 * @param {string} username - 销售用户名（可选）
 * @returns {Promise} 未发放提成订单列表
 */
export function getUnpaidOrders(startDate, endDate, username) {
  return request({
    url: '/commission-settlement/unpaid/orders',
    method: 'get',
    params: { start_date: startDate, end_date: endDate, username }
  })
}

/**
 * 标记提成已发放
 * @param {string} startDate - 结算开始日期，格式 YYYY-MM-DD
 * @param {string} endDate - 结算结束日期，格式 YYYY-MM-DD（含当天）
 * @param {string} username - 销售用户名（可选）
 * @returns {Promise} 发放结果
 */
export function payCommission(startDate, endDate, username) {
  return request({
    url: '/commission-settlement/pay',
    method: 'post',
    params: { start_date: startDate, end_date: endDate, username }
  })
}
