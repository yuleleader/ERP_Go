import request from '@/utils/request'

// 获取站内信列表
export function getNotifications(params) {
  return request({
    url: '/notifications/',
    method: 'get',
    params
  })
}

// 获取未读消息数量
export function getUnreadCount() {
  return request({
    url: '/notifications/unread-count',
    method: 'get'
  })
}

// 标记单条消息为已读
export function markAsRead(notificationId) {
  return request({
    url: `/notifications/${notificationId}/read`,
    method: 'put'
  })
}

// 标记所有消息为已读
export function markAllAsRead() {
  return request({
    url: '/notifications/all/read',
    method: 'put'
  })
}

// 删除单条消息
export function deleteNotification(notificationId) {
  return request({
    url: `/notifications/${notificationId}`,
    method: 'delete'
  })
}