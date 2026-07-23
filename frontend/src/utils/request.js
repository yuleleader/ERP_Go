import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { getBaseURL, getTimeout } from '@/api/baseUrl'

const request = axios.create({
  baseURL: getBaseURL(),
  timeout: getTimeout()
})

request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  response => {
    if (response.config.responseType === 'blob') {
      return response
    }
    return response.data
  },
  error => {
    console.error('请求错误详情:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
      code: error.code
    })
    
    if (error.response) {
      const { status, data } = error.response

      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem('token')
        router.push('/login')
      } else if (status === 403) {
        ElMessage.error(data.detail || '您没有权限执行此操作')
      } else if (status === 404) {
        ElMessage.error(data.detail || '请求的资源不存在')
      } else if (status === 500) {
        ElMessage.error('服务器错误，请稍后重试')
      } else {
        ElMessage.error(data.detail || `请求失败 (${status})`)
      }
    } else if (error.request) {
      ElMessage.error(`请求超时或服务器未响应: ${error.message}`)
    } else {
      ElMessage.error(`请求配置错误: ${error.message}`)
    }
    return Promise.reject(error)
  }
)

export default request
