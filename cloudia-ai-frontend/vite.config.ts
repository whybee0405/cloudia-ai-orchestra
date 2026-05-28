import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api/brand': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/campaigns': { target: 'http://localhost:8001', changeOrigin: true },
      '/api/ads': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/webdev': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        headers: { 'X-API-Key': process.env.WEBDEV_SECRET_KEY ?? '' },
      },
      '/internal': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
