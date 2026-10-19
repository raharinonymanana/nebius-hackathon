import dns from 'node:dns'
import net from 'node:net'
// Happy Eyeballs races IPv6+IPv4 and times out on this network (dead IPv6 route);
// force a single IPv4 connect so the dev proxy can reach the Lambda.
dns.setDefaultResultOrder('ipv4first')
net.setDefaultAutoSelectFamily(false)

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // In dev, fetch('/api/...') hits the real deployed backend.
      '/api': {
        target:
          'https://h5cgebthqaawxpwe4tcutkzl540fshgj.lambda-url.us-east-1.on.aws',
        changeOrigin: true,
        secure: true,
        timeout: 60000,
        proxyTimeout: 60000,
        configure: (proxy) => {
          proxy.on('error', (err, _req, _res) => {
            console.error('[vite proxy] /api error:', err.message)
          })
        },
      },
    },
  },
})
