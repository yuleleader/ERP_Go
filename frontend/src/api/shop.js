import request from '@/utils/request'

export function getShops(params) {
  return request({
    url: '/shops/',
    method: 'get',
    params
  })
}

export function getShop(shopId) {
  return request({
    url: `/shops/${shopId}`,
    method: 'get'
  })
}

export function createShop(data) {
  return request({
    url: '/shops/',
    method: 'post',
    data
  })
}

export function updateShop(shopId, data) {
  return request({
    url: `/shops/${shopId}`,
    method: 'put',
    data
  })
}

export function deleteShop(shopId) {
  return request({
    url: `/shops/${shopId}`,
    method: 'delete'
  })
}

export function syncShopOrders(shopId) {
  return request({
    url: `/shops/${shopId}/sync`,
    method: 'post'
  })
}
