export const TARGET = 'ormar'
// Backend replay budget is 40s plus ~12s cold-start overhead (worst ~52s).
// Give the browser headroom above that so the backend's own graceful
// NOT-PROVEN reply wins over a client-side abort.
export const TIMEOUT_MS = 55000
