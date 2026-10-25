# frontend — Mélodie terminal UI

Vite + React + TypeScript, built as a static bundle (no CDN; JetBrains Mono is self-hosted via @fontsource).
The Lambda in `demo/` serves the built files plus the two API routes the UI calls:
`GET /api/data` (the frozen eval/replay contract) and `POST /api/verify` (a live sandbox verify).

```bash
npm ci
npm run dev     # dev server; proxies /api/* to the deployed Lambda
npm run test    # Vitest unit tests (contract normalisation)
npm run lint    # oxlint
npm run build   # tsc -b && vite build -> dist/
```

See the root README for the architecture and deployment.
