import request from '@/utils/request'

/**
 * 获取网店列表（按创建者分组）
 * @param {string} keyword - 搜索关键词
 * @returns {Promise} 分组后的网店列表
 */
export function getWithdrawShops(keyword) {
  return request({
    url: '/withdraw/shops',
    method: 'get',
    params: { keyword }
  })
}

/**
 * 获取提现记录列表
 * @param {string} shop_id - 网店ID
 * @param {Object} params - 查询参数（日期范围、金额范围、分页等）
 * @returns {Promise} 提现记录列表
 */
export function getWithdrawRecords(shop_id, params) {
  return request({
    url: '/withdraw/records',
    method: 'get',
    params: { shop_id, ...params }
  })
}

/**
 * 新增提现记录
 * @param {Object} data - 提现记录数据
 * @returns {Promise} 创建结果
 */
export function createWithdrawRecord(data) {
  return request({
    url: '/withdraw/records',
    method: 'post',
    data
  })
}

/**
 * 更新提现记录
 * @param {number} record_id - 记录ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export function updateWithdrawRecord(record_id, data) {
  return request({
    url: `/withdraw/records/${record_id}`,
    method: 'put',
    data
  })
}

/**
 * 删除提现记录
 * @param {number} record_id - 记录ID
 * @returns {Promise} 删除结果
 */
export function deleteWithdrawRecord(record_id) {
  return request({
    url: `/withdraw/records/${record_id}`,
    method: 'delete'
  })
}

/**
 * 导出提现记录
 * @param {string} shop_id - 网店ID
 * @param {Object} params - 筛选参数
 * @returns {Promise} 导出文件流
 */
export function exportWithdrawRecords(shop_id, params) {
  return request({
    url: '/withdraw/records/export',
    method: 'get',
    params: { shop_id, ...params },
    responseType: 'blob'
  })
}
