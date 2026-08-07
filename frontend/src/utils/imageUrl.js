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

/**
 * 将图片保存到设备（手机端：点击"保存"触发下载）。
 * - Android Chrome/Edge：blob + a[download] 直接保存到下载目录/相册
 * - iOS Safari：保存到"文件"App（iOS 13+）；如需存相册可在预览界面长按图片
 *   走系统菜单"存储图像"
 * - 失败时降级：新窗口打开原图，用户可长按保存
 * @param {string} url - 图片完整 URL（可含 ?token=）
 * @returns {Promise<boolean>} 是否成功触发保存
 */
export async function saveImageByUrl(url) {
  if (!url) return false
  try {
    const resp = await fetch(url)
    if (!resp.ok) throw new Error(`fetch ${resp.status}`)
    const blob = await resp.blob()
    let ext = (blob.type || 'image/jpeg').split('/')[1] || 'jpg'
    if (ext === 'jpeg') ext = 'jpg'
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `image_${Date.now()}.${ext}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(a.href), 5000)
    return true
  } catch (e) {
    // 降级：新窗口打开原图（用户可长按/右键保存）
    try {
      window.open(url, '_blank')
    } catch (e2) {
      /* ignore */
    }
    return false
  }
}

export default { imageUrlWithToken, saveImageByUrl }