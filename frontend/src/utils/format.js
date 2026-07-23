// 时间格式化统一工具：所有时间一律按「北京时间（Asia/Shanghai, UTC+8）」显示，
// 不依赖浏览器/服务器所在时区。后端返回的时间统一为北京时间语义。

// 将任意时间输入（Date / ISO字符串 / 空格分隔的北京时间字符串）解析为真实 UTC 时刻的 Date
function toBeijingDate(value) {
  if (!value) return null
  if (value instanceof Date) return isNaN(value.getTime()) ? null : value
  let s = String(value).trim().replace(' ', 'T')
  // 若无时区标记，则按北京时间（UTC+8）解析，确保跨时区一致
  if (!/[zZ]$/.test(s) && !/[+-]\d{2}:?\d{2}$/.test(s)) {
    s += '+08:00'
  }
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

// 提取北京时间各分量（toBeijingDate 已包含 +8h 偏移，这里取 UTC 分量即为北京显示值）
function beijingParts(value) {
  const d = toBeijingDate(value)
  if (!d) return null
  const bj = new Date(d.getTime() + 8 * 3600 * 1000)
  return {
    y: bj.getUTCFullYear(),
    mo: String(bj.getUTCMonth() + 1).padStart(2, '0'),
    da: String(bj.getUTCDate()).padStart(2, '0'),
    h: String(bj.getUTCHours()).padStart(2, '0'),
    mi: String(bj.getUTCMinutes()).padStart(2, '0'),
    s: String(bj.getUTCSeconds()).padStart(2, '0')
  }
}

// 完整日期时间：YYYY-MM-DD HH:MM:SS
export function formatDateTime(date) {
  const p = beijingParts(date)
  if (!p) return ''
  return `${p.y}-${p.mo}-${p.da} ${p.h}:${p.mi}:${p.s}`
}

// 仅日期：YYYY-MM-DD
export function formatDate(date) {
  const p = beijingParts(date)
  if (!p) return ''
  return `${p.y}-${p.mo}-${p.da}`
}

export const formatDateOnly = formatDate

// 当前北京时间（YYYY-MM-DD），用于表单默认日期等
export function todayBeijing() {
  return formatDate(new Date())
}

export { toBeijingDate }
