import request from '@/utils/request'

// ==================== 账务代码（老板维护） ====================
export function getAccountingCodes(params) {
  return request({
    url: '/accounting-codes/',
    method: 'get',
    params
  })
}

export function createAccountingCode(data) {
  return request({
    url: '/accounting-codes/',
    method: 'post',
    data
  })
}

export function updateAccountingCode(id, data) {
  return request({
    url: `/accounting-codes/${id}`,
    method: 'put',
    data
  })
}

export function deleteAccountingCode(id) {
  return request({
    url: `/accounting-codes/${id}`,
    method: 'delete'
  })
}

// ==================== 非交易收支流水 ====================
// 当前用户自己创建的网店（录入时关联网店下拉）
export function getMyShops() {
  return request({
    url: '/non-trade-transactions/my-shops',
    method: 'get'
  })
}

export function getNonTradeTransactions(params) {
  return request({
    url: '/non-trade-transactions/',
    method: 'get',
    params
  })
}

export function createNonTradeTransaction(data) {
  return request({
    url: '/non-trade-transactions/',
    method: 'post',
    data
  })
}

export function updateNonTradeTransaction(id, data) {
  return request({
    url: `/non-trade-transactions/${id}`,
    method: 'put',
    data
  })
}

export function deleteNonTradeTransaction(id) {
  return request({
    url: `/non-trade-transactions/${id}`,
    method: 'delete'
  })
}

// 非交易收支统计报表（仅老板端）
export function getNonTradeSummary(params) {
  return request({
    url: '/non-trade-transactions/summary',
    method: 'get',
    params
  })
}
