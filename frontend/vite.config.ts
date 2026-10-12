import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // In dev, fetch('/api/data') hits the real deployed backend.
      '/api': {
        target:
          'https://h5cgebthqaawxpwe4tcutkzl540fshgj.lambda-url.us-east-1.on.aws',
        changeOrigin: true,
        secure: true,
      },
    },
  },
})
