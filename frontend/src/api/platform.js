import request from '@/utils/request'

// 平台管理接口（基础信息-平台管理，仅老板端）

export function getPlatforms(params) {
  return request({
    url: '/platforms/',
    method: 'get',
    params
  })
}

export function createPlatform(data) {
  return request({
    url: '/platforms/',
    method: 'post',
    data
  })
}

export function updatePlatform(platformCode, data) {
  return request({
    url: `/platforms/${platformCode}`,
    method: 'put',
    data
  })
}

export function deletePlatform(platformCode) {
  return request({
    url: `/platforms/${platformCode}`,
    method: 'delete'
  })
}
