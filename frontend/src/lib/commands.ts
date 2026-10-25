import type { Contract } from './contract'
import { TARGET } from './config'

// /help output. Lists ONLY what is actually built — no invented commands, no
// unbuilt keys (e.g. esc). Kept in sync with onSubmit's slash dispatch below.
export const HELP = `commands
  /help      show this help
  /clear     clear the transcript
  /eval      evaluation table (pass@k, Wilson 95%)
  /classes   supported CVE classes + status
  /receipts  replay receipts on disk
  /scope     what Mélodie does and does not do
  /version   build + data provenance
keys
  ⏎          verify the current input
  ↑ / ↓      walk input history`

// Headline eval rate for a target card, if the eval table carries one.
// Self-labeling (the axis names itself), returns null when none applies
// (e.g. a handed target with no unaided rate). Reads loaded data only.
export function evalRate(ev: Contract['eval'], targetId: string): string | null {
  const short = targetId.split('-')[0]
  for (const kw of ['weaponise', 'locate']) {
    const r = ev.rows.find(
      (row) =>
        row.kind === 'rate' &&
        row.target === short &&
        row.axis.includes(kw) &&
        row.ci_lo !== null,
    )
    if (r && r.kind === 'rate') {
      const label = r.axis.split(' ')[0]
      return `${label} ${r.rate_str} ${r.ci_str}`
    }
  }
  return null
}

// --- Data slash-commands. Each renders through the 'output' entry kind and reads
// only the already-loaded Contract (no model / API / Tavily call). ---

export const SCOPE_BODY = `Mélodie confirms a KNOWN finding by replaying a proof-of-concept
in a sealed, model-free sandbox and canary-checking the result.

IT IS      exploit validation — PROVEN / NOT PROVEN / FIX VERIFIED,
           decided only by the canary, never by a model.
IT IS NOT  discovery, scanning, fuzzing, or arbitrary-CVE coverage.

Supported classes: SQL injection, path traversal, command injection.`

export function evalBody(c: Contract): string {
  const ev = c.eval
  const tW = Math.max(8, ...ev.rows.map((r) => r.target.length))
  const aW = Math.max(8, ...ev.rows.map((r) => r.axis.length))
  const lines: string[] = []
  const sections: string[] = []
  for (const r of ev.rows) if (!sections.includes(r.section)) sections.push(r.section)
  for (const sec of sections) {
    lines.push(sec.toUpperCase())
    for (const r of ev.rows.filter((x) => x.section === sec)) {
      const val = r.ci_str ? `${r.rate_str}  ${r.ci_str}` : r.rate_str
      lines.push(`  ${r.target.padEnd(tW)}  ${r.axis.padEnd(aW)}  ${val}`)
    }
    lines.push('')
  }
  if (ev.remediation.length) {
    lines.push('REMEDIATION')
    const rW = Math.max(8, ...ev.remediation.map((r) => r.target.length))
    for (const rm of ev.remediation) {
      const verdict = rm.verified ? 'FIX VERIFIED' : 'FIX NOT VERIFIED'
      const attempt = `attempt ${rm.first_verified_attempt}/${rm.attempts}`
      lines.push(
        `  ${rm.target.padEnd(rW)}  ${verdict.padEnd(16)}  ${attempt}${rm.note ? '  — ' + rm.note : ''}`,
      )
    }
    lines.push('')
  }
  if (ev.notes.length) {
    lines.push('NOTES')
    for (const n of ev.notes) lines.push(`  · ${n}`)
  }
  return lines.join('\n').trimEnd()
}

export function classesBody(c: Contract): string {
  return c.targets
    .map((t) => {
      const status = t.id.startsWith(TARGET) ? 'LIVE' : 'REPLAY'
      const rate = evalRate(c.eval, t.id) ?? '—'
      return [
        `${t.cve}  [${status}]`,
        `  class     ${t.exploit_class}`,
        `  version   ${t.vulnerable_version} → ${t.fixed_version}`,
        `  unaided   ${rate}`,
      ].join('\n')
    })
    .join('\n\n')
}

export function receiptsBody(c: Contract): string {
  const m = c.meta
  const lines: string[] = [
    `${m.receipts_valid} valid receipts (${m.receipts_excluded} excluded) · model-free replay`,
    '',
  ]
  for (const t of c.targets) {
    lines.push(t.cve)
    const rows: Array<[string, { verdict: string; source_receipt: string } | null]> = [
      ['proven', t.runs.proven],
      ['not_proven', t.runs.not_proven],
      ['fix_verified', t.runs.fix_verified],
    ]
    for (const [label, run] of rows) {
      if (run) lines.push(`  ${label.padEnd(12)} ${run.verdict.padEnd(13)} ${run.source_receipt}`)
    }
    lines.push('')
  }
  return lines.join('\n').trimEnd()
}

export function versionBody(c: Contract): string {
  const m = c.meta
  return [
    `schema        v${c.schema_version}`,
    `data built    ${c.generated_utc}`,
    `receipts      ${m.receipts_valid} valid, ${m.receipts_excluded} excluded`,
    `model calls   ${m.model_calls}`,
    `model cost    $${m.model_cost_usd.toFixed(2)}`,
    `tavily        ${m.tavily_credits} credits`,
  ].join('\n')
}

// The slash-commands that render through the 'output' entry kind (same values,
// same order as onSubmit's dispatch).
export const DATA_COMMANDS = ['eval', 'classes', 'receipts', 'scope', 'version'] as const

export function buildCommand(name: string, c: Contract): { title: string; body: string } {
  switch (name) {
    case 'eval': return { title: 'eval', body: evalBody(c) }
    case 'classes': return { title: 'classes', body: classesBody(c) }
    case 'receipts': return { title: 'receipts', body: receiptsBody(c) }
    case 'scope': return { title: 'scope', body: SCOPE_BODY }
    case 'version': return { title: 'version', body: versionBody(c) }
    default: return { title: name, body: '' }
  }
}
