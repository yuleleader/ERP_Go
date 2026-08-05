import request from '@/utils/request'

// ==================== 智慧大屏专用API接口 ====================

/**
 * 测试API连接
 * @returns {Object} 测试结果
 */
export async function testApiConnection() {
  try {
    const response = await request({
      url: '/dashboard/test',
      method: 'get'
    })
    console.log('✅ API连接测试成功:', response)
    return response
  } catch (error) {
    console.error('❌ API连接测试失败:', error)
    throw error
  }
}

/**
 * 获取订单总览数据
 * @returns {Object} 订单统计数据
 */
export function getOrderOverview() {
  return request({
    url: '/dashboard/overview',
    method: 'get'
  })
}

/**
 * 获取销售排行榜数据
 * @param {Object} params - 查询参数
 * @param {number} params.limit - 返回数量限制
 * @returns {Object} 销售排行榜数据
 */
export function getSalesRanking(params = {}) {
  return request({
    url: '/dashboard/sales-ranking',
    method: 'get',
    params
  })
}

/**
 * 获取财务汇总数据
 * @param {Object} params - 查询参数
 * @param {string} params.period - 统计周期(week/month/quarter/year)
 * @returns {Object} 财务汇总数据
 */
export function getFinanceStatistics(params = {}) {
  return request({
    url: '/dashboard/finance-summary',
    method: 'get',
    params
  })
}

/**
 * 获取销售业绩详情数据
 * @returns {Object} 销售业绩数据
 */
export function getSalesPerformance() {
  return request({
    url: '/dashboard/sales-performance',
    method: 'get'
  })
}

/**
 * 获取商品热销排行榜数据
 * @param {Object} params - 查询参数
 * @param {number} params.limit - 返回数量限制
 * @returns {Object} 商品排行榜数据
 */
export function getProductRanking(params = {}) {
  return request({
    url: '/dashboard/product-ranking',
    method: 'get',
    params
  })
}

/**
 * 获取月度销售趋势
 * @param {Object} params - 查询参数
 * @param {number} params.months - 月份数量（默认24）
 * @returns {Object} 月度销售趋势数据
 */
export function getMonthlySales(params = {}) {
  return request({
    url: '/dashboard/monthly-sales',
    method: 'get',
    params
  })
}

/**
 * 获取网店销售排行
 * @param {Object} params - 查询参数
 * @param {number} params.limit - 返回数量限制
 * @returns {Object} 网店销售排行数据
 */
export function getShopRanking(params = {}) {
  return request({
    url: '/dashboard/shop-ranking',
    method: 'get',
    params
  })
}

/**
 * 获取超期订单
 * @param {Object} params - 查询参数
 * @param {number} params.limit - 返回数量限制
 * @returns {Object} 超期订单数据
 */
export function getOverdueOrders(params = {}) {
  return request({
    url: '/dashboard/overdue-orders',
    method: 'get',
    params
  })
}

/**
 * 获取订单国家分布（按收货地址离线识别国家后聚合）
 * @returns {Object} 每个国家的订单分布：总金额/总单数/已发货/未发货
 */
export function getCountryDistribution() {
  return request({
    url: '/dashboard/country-distribution',
    method: 'get'
  })
}