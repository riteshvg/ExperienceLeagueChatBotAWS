import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

const isProd = process.env.NODE_ENV === 'production'
const apiPort = process.env.ROVR_API_PORT ?? '8000'

export default defineConfig({
  base: isProd ? '/tools/rovr/' : '/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': `http://localhost:${apiPort}`,
    },
  },
})
