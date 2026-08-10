import request from '@/utils/request'

/**
 * 超期预警：按销售员分组返回超期未生产/未发货订单
 * @param {Object} params - { days: 超期天数（可选，默认系统参数） }
 */
export function getOverdueWarnings(params) {
  return request({
    url: '/warnings/overdue',
    method: 'get',
    params
  })
}
