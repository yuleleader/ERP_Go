import request from '@/utils/request'

/**
 * 下载 Excel 导入模板（含列名 + 案例数据）
 */
export function downloadImportTemplate() {
  return request({
    url: '/order-imports/template',
    method: 'get',
    responseType: 'blob'
  })
}

/**
 * 上传 Excel 导入临时表（返回批次号）
 * @param {File} file
 */
export function importOrderExcel(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/order-imports/import',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000
  })
}

/**
 * 临时表列表
 */
export function getOrderImports(params) {
  return request({
    url: '/order-imports/',
    method: 'get',
    params
  })
}

/**
 * 编辑临时表行（保存后重新计算异常，需再次审核）
 * @param {number} id
 * @param {Object} data
 */
export function updateOrderImport(id, data) {
  return request({
    url: `/order-imports/${id}`,
    method: 'put',
    data
  })
}

/**
 * 审核合并：仅无异常行可合并，合并后临时记录移除
 * @param {Array<number>} ids
 */
export function mergeOrderImports(ids) {
  return request({
    url: '/order-imports/merge',
    method: 'post',
    data: { ids }
  })
}

/**
 * 删除单条临时记录
 * @param {number} id
 */
export function deleteOrderImport(id) {
  return request({
    url: `/order-imports/${id}`,
    method: 'delete'
  })
}

/**
 * 批量删除临时记录
 * @param {Array<number>} ids
 */
export function deleteBatchOrderImports(ids) {
  return request({
    url: '/order-imports/delete-batch',
    method: 'post',
    data: { ids }
  })
}
