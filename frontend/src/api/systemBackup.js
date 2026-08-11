import request from '@/utils/request'

// 读取启动器备份状态（备份配置 + 最近备份日志）
export function getBackupState() {
  return request({
    url: '/system-backup/state',
    method: 'get'
  })
}

// 触发立即备份
export function runBackupNow() {
  return request({
    url: '/system-backup/run',
    method: 'post'
  })
}

// 保存自动备份设置
export function saveBackupConfig(payload) {
  return request({
    url: '/system-backup/config',
    method: 'post',
    data: payload
  })
}
