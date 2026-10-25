// Types mirroring demo/demo_data.json EXACTLY.
// Field names, nullability and the literal `verdict` / `kind` strings are copied
// verbatim from the real file, not guessed. `verdict` and `kind` are the
// discriminants, so human_trace is structurally proven-only (the compiler
// rejects a human_trace on any run that is not PROVEN).

export interface Meta {
  model_cost_usd: number
  model_calls: number
  tavily_credits: number
  receipts_valid: number
  receipts_excluded: number
}

// One structured trace step (verify_service emits these alongside human_trace).
// Additive: the UI prefers steps[] when present, else falls back to human_trace.
export interface Step {
  name: string
  status: 'ok' | 'fail' | 'skipped'
  decided: boolean
  seconds: number | null
}

// Fields shared by every run variant (demo_data.json: present on all three).
interface RunBase {
  mode: 'unaided' | 'handed'
  // null on some runs (e.g. starlette.not_proven, where no payload was submitted).
  input: string | null
  canary: string
  model: string
  verification_is_model_free: boolean
  utc: string
  source_receipt: string
  // Optional on every variant: present on live PROVEN / NOT PROVEN runs from
  // verify_service; absent on older receipts — do not make required.
  steps?: Step[]
}

// One Tavily-cited advisory source: the top-scored one the harness kept.
export interface AdvisorySource {
  url: string
  title: string
  score: number
}

// Trimmed Tavily advisory surfaced on a proven run — CVE + fix version, the
// single top cited source, and how many sources the harness discarded as
// non-advisory. Optional: older receipts predate it (same additive rule as steps[]).
export interface Advisory {
  provider: string
  cve: string
  fixed_version: string | null
  top_source: AdvisorySource | null
  discarded_count: number
}

// verdict "PROVEN": the only variant that carries human_trace (required here).
export interface ProvenRun extends RunBase {
  verdict: 'PROVEN'
  human_trace: string[]
  advisory?: Advisory
}

// verdict "NOT PROVEN": no human_trace, no exploit_closed / still_works.
export interface NotProvenRun extends RunBase {
  verdict: 'NOT PROVEN'
}

// verdict "FIX VERIFIED": carries the remediation outcome fields.
export interface FixVerifiedRun extends RunBase {
  verdict: 'FIX VERIFIED'
  exploit_closed: boolean
  still_works: boolean
}

export type Run = ProvenRun | NotProvenRun | FixVerifiedRun

export interface Target {
  id: string
  name: string
  cve: string
  exploit_class: string
  vulnerable_version: string
  fixed_version: string
  runs: {
    proven: ProvenRun
    // null when no standalone fixed/NOT-PROVEN receipt exists (e.g. ormar).
    not_proven: NotProvenRun | null
    fix_verified: FixVerifiedRun
  }
}

// Fields shared by every eval row (demo_data.json: present on rate and count).
interface EvalRowBase {
  section: string
  target: string
  axis: string
  n: number
  rate_str: string
  ci_str: string
}

// kind "rate": carries x and the confidence interval (ci_* null, e.g. ormar
// discrimination). x is always a number in the file.
export interface RateRow extends EvalRowBase {
  kind: 'rate'
  x: number
  ci_lo: number | null
  ci_hi: number | null
}

// kind "count": carries count instead of x / ci_lo / ci_hi.
export interface CountRow extends EvalRowBase {
  kind: 'count'
  count: number
}

export type EvalRow = RateRow | CountRow

export interface RemediationRow {
  target: string
  verified: boolean
  cell: string
  attempts: number
  first_verified_attempt: number
  note: string | null
}

export interface Eval {
  rows: EvalRow[]
  remediation: RemediationRow[]
  notes: string[]
}

export interface Contract {
  schema_version: number
  generated_utc: string
  meta: Meta
  targets: Target[]
  eval: Eval
}
