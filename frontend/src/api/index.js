/**
 * API接口统一导出入口
 * 所有业务接口由此对外暴露，禁止直接导入子文件
 */

// 认证相关接口
export * as authApi from './auth'

// 用户管理接口
export * as userApi from './user'

// 网店管理接口
export * as shopApi from './shop'

// 物流公司管理接口
export * as logisticsApi from './logistics'

// 订单管理接口
export * as orderApi from './order'

// 图片管理接口
export * as imageApi from './image'

// 数据统计接口
export * as statisticsApi from './statistics'

// 日志管理接口
export * as logApi from './logs'

// 商品管理接口
export * as productApi from './product'

// 通知管理接口
export * as notificationApi from './notification'

// 汇率接口
export * as exchangeApi from './exchange'

// 工作台接口
export * as dashboardApi from './dashboard'

// 提成结算接口
export * as commissionSettlementApi from './commission_settlement'

// 网店提现记录接口
export * as withdrawApi from './withdraw'