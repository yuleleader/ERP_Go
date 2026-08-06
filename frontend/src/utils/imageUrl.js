/**
 * 给后端鉴权的图片 URL 追加 ?token=xxx（serve_router 接受 Authorization header 或 ?token= 查询参数）。
 * 由于浏览器 <img>/el-image 不会带自定义请求头，图片 src 必须显式拼接 token 才能正常显示。
 * @param {string} url - 后端返回的图片 URL（可能是 /data/images/... 相对路径或完整 URL）
 */
export function imageUrlWithToken(url) {
  if (!url) return url
  // 绝对地址（http/https）或 data: 直接返回
  if (/^(https?:|data:)/i.test(url)) return url

  const token = localStorage.getItem('token')
  if (!token) return url

  // 已经是相对路径，前端 vue.config/vite proxy 会代发；只是需附上 token
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}token=${encodeURIComponent(token)}`
}

export default { imageUrlWithToken }