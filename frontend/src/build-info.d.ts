// Compile-time build identity, injected by vite.config.ts `define` from
// demo/build_info.json. null when the file is absent (e.g. `npm run dev`).
// Keep this shape in sync with demo/build_info.py.
declare const __BUILD_INFO__: {
  name: string
  version: string
  commit: string
  built_utc: string | null
} | null
