// Types mirroring demo/demo_data.json EXACTLY.
// Field names and nullability are derived from the real file, not guessed.

export interface Meta {
  model_cost_usd: number
  model_calls: number
  tavily_credits: number
  receipts_valid: number
  receipts_excluded: number
}

// One run of the prover against a target variant. The three variants in
// `Target.runs` (proven / not_proven / fix_verified) all share the base
// fields below; the trailing fields appear only on specific variants.
export interface Run {
  verdict: string
  mode: string
  // null on some runs (e.g. starlette.not_proven, where no payload was submitted).
  input: string | null
  canary: string
  model: string
  verification_is_model_free: boolean
  utc: string
  source_receipt: string
  // Present on the `proven` variant only.
  human_trace?: string[]
  // Present on the `fix_verified` variant only.
  exploit_closed?: boolean
  still_works?: boolean
}

export interface Target {
  id: string
  name: string
  cve: string
  exploit_class: string
  vulnerable_version: string
  fixed_version: string
  runs: {
    proven: Run
    // null when no standalone fixed/NOT-PROVEN receipt exists (e.g. ormar).
    not_proven: Run | null
    fix_verified: Run
  }
}

// A row in eval.rows. `kind` is "rate" or "count":
//  - rate rows carry x, ci_lo, ci_hi (ci_* may be null, e.g. ormar discrimination).
//  - count rows carry count (and no x / ci_lo / ci_hi).
export interface EvalRow {
  section: string
  target: string
  axis: string
  kind: string
  n: number
  rate_str: string
  ci_str: string
  x?: number
  ci_lo?: number | null
  ci_hi?: number | null
  count?: number
}

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
