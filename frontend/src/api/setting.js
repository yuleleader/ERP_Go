/**
 * 系统参数 API
 */
import request from '@/utils/request'

// 获取全部系统参数（缺失项用默认值补齐）
export function getSettings() {
  return request({
    url: '/settings',
    method: 'get'
  })
}

// 批量更新系统参数（仅老板端）
export function updateSettings(items) {
  return request({
    url: '/settings',
    method: 'post',
    data: { items }
  })
}
