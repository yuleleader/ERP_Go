/**
 * 全模块数据权限配置（2026-08-12 扩展版）。
 *
 * 结构：一级模块 → 分组 → 页面；每个页面的可用操作按页面性质定制。
 * 操作码：query 查询 / add 新增 / edit 修改 / delete 删除 / export 导出
 *
 * 规则约束：
 * - query 是页面可见性的开关 —— 某页面未勾选「查询」，则该二级菜单不可见，其增删改导出权限同步失效；
 * - 老板端（boss）恒有全部权限，不参与勾选判断；
 * - 旧版键 category/brand/product 自动映射到 /categories /brands /products（旧数据兼容）。
 */
export const PERM_TREE = [
  {
    key: 'orders',
    title: '订单管理',
    pages: [
      { path: '/orders', label: '订单管理', actions: ['query', 'export'] }
    ]
  },
  {
    key: 'basic',
    title: '基础信息',
    groups: [
      {
        title: '商品资料',
        pages: [
          { path: '/products', label: '商品管理', actions: ['query', 'add', 'edit', 'delete'] },
          { path: '/categories', label: '类别管理', actions: ['query', 'add', 'edit', 'delete'] },
          { path: '/brands', label: '品牌管理', actions: ['query', 'add', 'edit', 'delete'] }
        ]
      },
      {
        title: '店铺物流',
        pages: [
          { path: '/shops', label: '网店信息', actions: ['query', 'add', 'edit', 'delete'] },
          { path: '/logistics', label: '物流管理', actions: ['query', 'add', 'edit', 'delete'] }
        ]
      }
    ]
  },
  {
    key: 'statistics',
    title: '数据统计',
    groups: [
      { title: '数据概览', pages: [{ path: '/statistics', label: '数据总览', actions: ['query'] }] },
      {
        title: '销售分析',
        pages: [
          { path: '/sales-statistics', label: '销售统计', actions: ['query', 'export'] },
          { path: '/gross-profit-analysis', label: '毛利分析', actions: ['query', 'export'] },
          { path: '/shop-sales-statistics', label: '网店销售统计', actions: ['query', 'export'] },
          { path: '/refund-orders', label: '退款订单', actions: ['query', 'export'] },
          { path: '/refund-rate-analysis', label: '退款率分析', actions: ['query', 'export'] }
        ]
      },
      { title: '预警管理', pages: [{ path: '/warnings', label: '预警中心', actions: ['query'] }] },
      { title: '提成核算', pages: [{ path: '/commission-statistics', label: '销售提成统计', actions: ['query'] }] }
    ]
  },
  {
    key: 'finance',
    title: '财务模块',
    groups: [
      {
        title: '财务结算',
        pages: [
          { path: '/salary-settlement', label: '工资结算', actions: ['query', 'edit'] },
          { path: '/account-withdrawal', label: '账户提现', actions: ['query', 'add', 'edit'] }
        ]
      },
      { title: '费用统计', pages: [{ path: '/freight-statistics', label: '运费统计', actions: ['query', 'export'] }] },
      {
        title: '非交易收支',
        pages: [
          { path: '/accounting-codes', label: '账务代码', actions: ['query', 'add', 'edit', 'delete'] },
          { path: '/non-trade-transactions', label: '收支录入', actions: ['query', 'add', 'edit', 'delete'] },
          { path: '/non-trade-summary', label: '收支统计', actions: ['query', 'export'] }
        ]
      }
    ]
  },
  {
    key: 'system',
    title: '系统设置',
    groups: [
      { title: '账号权限', pages: [{ path: '/users', label: '用户管理', actions: ['query', 'add', 'edit', 'delete'] }] },
      {
        title: '消息通讯',
        pages: [
          { path: '/notifications', label: '站内信管理', actions: ['query', 'delete'] },
          { path: '/logs', label: '日志管理', actions: ['query'] },
          { path: '/system-backup', label: '系统备份', actions: ['query', 'edit'] }
        ]
      },
      {
        title: '系统运维',
        pages: [
          { path: '/settings', label: '系统参数', actions: ['query', 'edit'] },
          { path: '/data-cleanup', label: '日志清理', actions: ['query', 'edit'] },
          { path: '/order-imports', label: '数据导入', actions: ['query', 'add', 'edit', 'delete'] }
        ]
      },
      { title: '关于本系统', pages: [{ path: '/system-info', label: '系统信息', actions: ['query'] }] }
    ]
  }
]

// 旧版键 → 新路径键（兼容既有 {"category":["add"],...} 数据）
export const LEGACY_KEYS = { category: '/categories', brand: '/brands', product: '/products' }

// 操作码显示名
export const ACTION_LABELS = {
  query: '查询',
  add: '新增',
  edit: '修改',
  delete: '删除',
  export: '导出'
}

// 取某模块下全部页面（有 groups 走分组，无则用 pages）
export function modulePages(mod) {
  if (Array.isArray(mod.pages)) return mod.pages
  const out = []
  ;(mod.groups || []).forEach((g) => out.push(...g.pages))
  return out
}

// 展平全部页面
export function allPages() {
  const out = []
  PERM_TREE.forEach((mod) => out.push(...modulePages(mod)))
  return out
}

/**
 * 统一把任意权限对象解析为 { path: [actions...] }，兼容旧格式。
 * 旧格式 {category:["add"],...} 会转为路径键，且只要旧数据有任一操作，就补上 query（页面保持可见）。
 */
export function normalizePerms(raw) {
  const out = {}
  if (!raw) return out
  let o = raw
  try {
    o = typeof raw === 'string' ? JSON.parse(raw) : (raw || {})
  } catch (e) {
    return out
  }
  if (typeof o !== 'object' || o === null) return out
  for (const [oldKey, path] of Object.entries(LEGACY_KEYS)) {
    const arr = o[oldKey]
    if (Array.isArray(arr) && arr.length) {
      const list = [...new Set([...(out[path] || []), ...arr])]
      if (!list.includes('query')) list.push('query')
      out[path] = list
    }
  }
  for (const [key, value] of Object.entries(o)) {
    if (key in LEGACY_KEYS) continue
    if (Array.isArray(value)) out[key] = value.filter((a) => typeof a === 'string')
  }
  return out
}

/** 判断某用户对某页面是否拥有某操作（老板恒全权；旧键自动映射） */
export function hasPerm(userInfo, moduleOrPath, action) {
  if (!userInfo) return false
  if (userInfo.role === 'boss') return true
  const path = LEGACY_KEYS[moduleOrPath] || moduleOrPath
  const perms = normalizePerms(userInfo.data_permissions)
  const arr = perms[path]
  return Array.isArray(arr) && arr.includes(action)
}

/** 页面可见性判断：是否拥有「查询」权限 */
export function canQuery(userInfo, moduleOrPath) {
  return hasPerm(userInfo, moduleOrPath, 'query')
}
