import request from '@/utils/request'

// 获取物流公司列表
export async function getLogisticsCompanies() {
  const response = await request.get('/logistics/companies')
  return response
}

// 创建物流公司
export async function createLogisticsCompany(data) {
  const response = await request.post('/logistics/companies', data)
  return response
}

// 更新物流公司
export async function updateLogisticsCompany(id, data) {
  const response = await request.put(`/logistics/companies/${id}`, data)
  return response
}

// 删除物流公司
export async function deleteLogisticsCompany(id) {
  const response = await request.delete(`/logistics/companies/${id}`)
  return response
}
