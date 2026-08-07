/**
 * 账号级数据权限判断（类别/品牌/商品档案 × 新增/修改/删除）。
 * data_permissions 为 JSON 字符串，如 {"category":["add"],"product":["edit"]}；
 * 老板端恒有全部权限；未授权返回 false。
 * @param {Object|null} userInfo - 当前用户信息（含 role / data_permissions）
 * @param {'category'|'brand'|'product'} module - 数据对象
 * @param {'add'|'edit'|'delete'} action - 操作
 */
export function checkDataPerm(userInfo, module, action) {
  if (!userInfo) return false
  if (userInfo.role === 'boss') return true
  const raw = userInfo.data_permissions
  if (!raw) return false
  try {
    const o = typeof raw === 'string' ? JSON.parse(raw) : (raw || {})
    return Array.isArray(o[module]) && o[module].includes(action)
  } catch (e) {
    return false
  }
}
