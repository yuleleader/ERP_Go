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