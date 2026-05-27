import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

client.interceptors.request.use(config => {
  const apiKey = localStorage.getItem('cloudia_api_key') || import.meta.env.VITE_API_KEY || ''
  config.headers['X-API-Key'] = apiKey
  return config
})

client.interceptors.response.use(
  res => res.data,
  err => {
    const message = err.response?.data?.detail || err.message || 'Unknown error'
    return Promise.reject(new Error(message))
  }
)

export default client
