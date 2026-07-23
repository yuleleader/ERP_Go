import request from '@/utils/request'

export function getUsers(params) {
  return request({
    url: '/users/',
    method: 'get',
    params
  })
}

export function getUser(userId) {
  return request({
    url: `/users/${userId}`,
    method: 'get'
  })
}

export function updateUser(userId, data) {
  return request({
    url: `/users/${userId}`,
    method: 'put',
    data
  })
}

export function deleteUser(userId) {
  return request({
    url: `/users/${userId}`,
    method: 'delete'
  })
}
