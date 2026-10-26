import dns from 'node:dns'
import net from 'node:net'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
// Happy Eyeballs races IPv6+IPv4 and times out on this network (dead IPv6 route);
// force a single IPv4 connect so the dev proxy can reach the Lambda.
dns.setDefaultResultOrder('ipv4first')
net.setDefaultAutoSelectFamily(false)

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Build identity, frozen per deploy by `python -m demo.build_info`. Read once at
// config load, resolved relative to THIS file (not cwd), and baked in as the
// compile-time constant __BUILD_INFO__ (null when the file is absent, e.g. dev).
const buildInfoPath = fileURLToPath(new URL('../demo/build_info.json', import.meta.url))
let buildInfo: unknown = null
try {
  buildInfo = JSON.parse(readFileSync(buildInfoPath, 'utf-8'))
} catch {
  buildInfo = null
}

// https://vite.dev/config/
export default defineConfig({
  define: {
    __BUILD_INFO__: JSON.stringify(buildInfo),
  },
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
