import { execSync } from 'child_process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

const isProd = process.env.NODE_ENV === 'production'
const apiPort = process.env.ROVR_API_PORT ?? '8000'

function currentGitBranch(): string {
  try {
    return execSync('git branch --show-current', { encoding: 'utf-8' }).trim()
  } catch {
    return ''
  }
}

const gitBranch = process.env.VITE_GIT_BRANCH ?? currentGitBranch()

export default defineConfig({
  base: isProd ? '/tools/rovr/' : '/',
  define: {
    'import.meta.env.VITE_GIT_BRANCH': JSON.stringify(gitBranch),
  },
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
