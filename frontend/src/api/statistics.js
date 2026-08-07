import request from '@/utils/request'

// 获取销售总金额统计
export function getTotalSales(params) {
  return request({
    url: '/statistics/sales/total',
    method: 'get',
    params
  })
}

// 获取理论应得提成（按销售时间统计）
export function getTheoreticalCommission(params) {
  return request({
    url: '/statistics/commission/theoretical',
    method: 'get',
    params
  })
}

// 获取实际应得提成（按发货时间统计）
export function getActualCommission(params) {
  return request({
    url: '/statistics/commission/actual',
    method: 'get',
    params
  })
}

// 获取每个销售用户的提成统计（按发货时间统计）- 仅老板端可用
export function getCommissionByUser(params) {
  return request({
    url: '/statistics/commission/by-user',
    method: 'get',
    params
  })
}

// 获取平均发货时长统计
export function getAvgShippingTime(params) {
  return request({
    url: '/statistics/avg-shipping-time',
    method: 'get',
    params
  })
}

// 获取工厂端工作台统计卡片数据（工厂端和老板端可用）
export function getFactoryDashboardStats() {
  return request({
    url: '/statistics/factory-dashboard',
    method: 'get'
  })
}

// 获取发货端工作台统计卡片数据（发货端可用）
export function getShippingDashboardStats() {
  return request({
    url: '/statistics/shipping-dashboard',
    method: 'get'
  })
}

// 获取综合统计概览
export function getOverviewStatistics(params) {
  return request({
    url: '/statistics/overview',
    method: 'get',
    params
  })
}

// 获取销售排行（老板端dashboard）
export function getDashboardSalesRanking(limit = 10) {
  return request({
    url: '/statistics/dashboard/sales-ranking',
    method: 'get',
    params: { limit }
  })
}

// 获取老板端工作台三段式流程图统计（销售 -> 生产 -> 发货）
export function getProcessFlow() {
  return request({
    url: '/statistics/process-flow',
    method: 'get'
  })
}

// 获取超期订单统计（老板端工作台经营概览卡片）
export function getOverdueOrders() {
  return request({
    url: '/statistics/overdue',
    method: 'get'
  })
}

// 销售汇总报表（人员/类别/品牌/商品）
// type: person/category/brand/product
export function getSalesSummary(params) {
  return request({
    url: '/statistics/sales-summary',
    method: 'get',
    params
  })
}

// 毛利分析明细（time_type: order=按下单时间 / shipping=按发货时间）
export function getGrossProfitList(params) {
  return request({
    url: '/statistics/gross-profit/list',
    method: 'get',
    params
  })
}

// 毛利分析下拉选项（销售人员/品牌/类别）
export function getGrossProfitOptions() {
  return request({
    url: '/statistics/gross-profit/options',
    method: 'get'
  })
}

// 运费统计（按下单时间筛选）
export function getFreightList(params) {
  return request({
    url: '/statistics/freight-list',
    method: 'get',
    params
  })
}

// 销售趋势（按下单时间按天汇总金额）
export function getSalesTrend(params) {
  return request({
    url: '/statistics/sales-trend',
    method: 'get',
    params
  })
}

// 销售统计下拉选项（人员/类别/品牌/商品）
export function getSalesSummaryOptions() {
  return request({
    url: '/statistics/sales-summary/options',
    method: 'get'
  })
}

// 网店销售统计（按网店分组）
export function getShopSalesSummary(params) {
  return request({
    url: '/statistics/shop-sales-summary',
    method: 'get',
    params
  })
}

// 汇总报表订单明细钻取（mode: shop=网店销售统计 / sales=销售统计）
export function getSummaryOrderDetails(params) {
  return request({
    url: '/statistics/summary-order-details',
    method: 'get',
    params
  })
}