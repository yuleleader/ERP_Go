import request from '@/utils/request'

export function getBrands() {
  return request({ url: '/brands/', method: 'get' })
}

export function createBrand(data) {
  return request({ url: '/brands/', method: 'post', data })
}

export function updateBrand(id, data) {
  return request({ url: `/brands/${id}`, method: 'put', data })
}

export function deleteBrand(id) {
  return request({ url: `/brands/${id}`, method: 'delete' })
}
