import request from '@/utils/request'

// ====================== 接口1：临时上传（创建订单前）======================
export function uploadTempImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/images/upload-temp',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// ====================== 接口2：迁移临时图到正式目录 ======================
export function migrateImage(tempId, orderId) {
  return request({
    url: `/images/migrate/${tempId}/${orderId}`,
    method: 'post'
  })
}

// ====================== 接口3：直接上传（已有订单）======================
export function uploadDirectImage(orderId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: `/images/upload-direct/${orderId}`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// ====================== 接口4：获取订单图片列表（新版）======================
export function getOrderImages(orderId) {
  return request({
    url: `/images/list/${orderId}`,
    method: 'get'
  })
}

// ====================== 接口5：删除图片 ======================
export function deleteImage(imageId) {
  return request({
    url: `/images/delete/${imageId}`,
    method: 'delete'
  })
}

// ====================== 接口6：设置主图 ======================
export function setMainImage(imageId) {
  return request({
    url: `/images/set-main/${imageId}`,
    method: 'post'
  })
}

// ====================== 接口6：清理临时图片（48小时过期）=====================
export function cleanTempImage() {
  return request({
    url: '/images/clean-temp',
    method: 'post'
  })
}

// ====================== 接口7：获取图片统计 ======================
export function getImageStats(layer) {
  return request({
    url: '/images/stats',
    method: 'get',
    params: { layer }
  })
}
