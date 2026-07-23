import request from '@/utils/request'

export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data: `username=${encodeURIComponent(data.username)}&password=${encodeURIComponent(data.password)}`,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })
}

export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}

export function getCurrentUser() {
  return request({
    url: '/auth/me',
    method: 'get'
  })
}

export function changePassword(oldPassword, newPassword) {
  return request({
    url: '/auth/password',
    method: 'put',
    data: { old_password: oldPassword, new_password: newPassword }
  })
}

export function resetPassword(userId) {
  return request({
    url: `/auth/reset-password/${userId}`,
    method: 'post'
  })
}
