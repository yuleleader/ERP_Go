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

// 401 全局防重：同一时刻多个请求同时 401 时只提示/跳转一次
let isRedirecting = false

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
        if (!isRedirecting) {
          isRedirecting = true
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          router.push('/login')
          // 短暂复位，避免同批并发 401 重复提示/跳转
          setTimeout(() => { isRedirecting = false }, 1000)
        }
      } else if (status === 403) {
        ElMessage.error(data.detail || '您没有权限执行此操作')
      } else if (status === 404) {
        ElMessage.error(data.detail || '请求的资源不存在')
      } else if (status === 422) {
        // 参数校验失败：detail 可能是数组（每个字段一条错误），转成可读文本
        const arr = Array.isArray(data?.detail) ? data.detail : []
        const msg = arr.length
          ? arr.map(item => item?.loc?.length > 1 ? `${item.loc[item.loc.length - 1]}：${item.msg}` : item.msg).join('；')
          : (typeof data?.detail === 'string' ? data.detail : '提交的数据格式不正确，请检查必填项')
        ElMessage.error(msg)
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

/**
 * 为图片地址追加登录令牌。
 * 后端 /data/images/* 已改为“必须登录”才能访问（替代原来的免登录直链），
 * 但 <img> 标签无法携带 Authorization 请求头，因此把令牌放在 URL 参数上传递。
 */
export function authImageUrl(url) {
  if (!url) return url
  const token = localStorage.getItem('token')
  if (!token) return url
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}token=${encodeURIComponent(token)}`
}

