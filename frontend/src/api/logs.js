import request from '@/utils/request'

export function getOperationLogs(params) {
  return request({
    url: '/logs/operations',
    method: 'get',
    params
  })
}

export function getLoginLogs(params) {
  return request({
    url: '/logs/login',
    method: 'get',
    params
  })
}

export function getCleanupConfig() {
  return request({
    url: '/logs/cleanup/config',
    method: 'get'
  })
}

export function updateCleanupConfig(data) {
  return request({
    url: '/logs/cleanup/config',
    method: 'put',
    data
  })
}

export function previewCleanup(data) {
  return request({
    url: '/logs/cleanup/preview',
    method: 'post',
    data
  })
}

export function executeCleanup(data) {
  return request({
    url: '/logs/cleanup/execute',
    method: 'post',
    data
  })
}

export function getCleanupRecords(params) {
  return request({
    url: '/logs/cleanup/records',
    method: 'get',
    params
  })
}

// ==================== 站内信清理 ====================

export function getNotificationCleanupConfig() {
  return request({
    url: '/logs/cleanup/notification/config',
    method: 'get'
  })
}

export function updateNotificationCleanupConfig(data) {
  return request({
    url: '/logs/cleanup/notification/config',
    method: 'put',
    data
  })
}

export function previewNotificationCleanup(data) {
  return request({
    url: '/logs/cleanup/notification/preview',
    method: 'post',
    data
  })
}

export function executeNotificationCleanup(data) {
  return request({
    url: '/logs/cleanup/notification/execute',
    method: 'post',
    data
  })
}