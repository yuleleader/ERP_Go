/**
 * 环境域名配置
 * 统一管理开发、测试、生产环境的API域名
 */

const env = process.env.NODE_ENV || 'development'

// 支持通过 Vite 构建环境变量 VITE_API_BASE_URL 覆盖默认同源地址
// 注意：必须用 import.meta.env（Vite 构建时静态替换），浏览器运行时不支持 process.env
const envBaseURL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) || ''

// 环境配置映射
const ENV_CONFIG = {
  development: {
    baseURL: envBaseURL || '/api',
    timeout: 30000
  },
  production: {
    baseURL: envBaseURL || '/api',
    timeout: 30000
  }
}

/**
 * 获取当前环境配置
 * @returns {Object} 当前环境的配置对象
 */
export function getEnvConfig() {
  return ENV_CONFIG[env] || ENV_CONFIG.development
}

/**
 * 获取API基础URL
 * @returns {string} API基础URL
 */
export function getBaseURL() {
  return getEnvConfig().baseURL
}

/**
 * 获取请求超时时间
 * @returns {number} 超时时间（毫秒）
 */
export function getTimeout() {
  return getEnvConfig().timeout
}

export default {
  getEnvConfig,
  getBaseURL,
  getTimeout
}