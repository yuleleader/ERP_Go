import axios from 'axios'

const exchangeRequest = axios.create({
  timeout: 15000
})

exchangeRequest.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    return Promise.reject(error)
  }
)

export default exchangeRequest
