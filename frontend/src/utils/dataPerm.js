/**
 * 账号级数据权限判断（全模块版，2026-08-12 扩展）。
 * data_permissions 为 JSON 字符串，如 {"/orders":["query","export"],"/products":["query","add","edit","delete"]}；
 * 兼容旧格式 {"category":["add"],"product":["edit"]}（旧键自动映射为路径键，且任一操作等价于可见该页）。
 * 老板端恒有全部权限；未授权返回 false。
 *
 * @param {Object|null} userInfo - 当前用户信息（含 role / data_permissions）
 * @param {string} module - 模块：旧键（category/brand/product）或路径键（如 '/orders'）
 * @param {string} action - 操作：query/add/edit/delete/export
 */
import { hasPerm } from './permTree'

export function checkDataPerm(userInfo, module, action) {
  return hasPerm(userInfo, module, action)
}

/** 页面可见性判断：是否拥有「查询」权限（老板恒 true） */
export function canQuery(userInfo, moduleOrPath) {
  return hasPerm(userInfo, moduleOrPath, 'query')
}
