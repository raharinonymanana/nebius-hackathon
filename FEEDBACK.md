## 2026-09-30 Token Factory
- Model IDs mix casing/naming styles (NVIDIA-Nemotron-3-Nano-30B-A3B vs nemotron-3-super-120b-a12b vs Nemotron-3_5-Lightning). Easy to mistype; a consistent slug convention would help.
- Output token counts can far exceed visible reply length (Lightning: 408 tokens for one sentence); would help if the usage object clearly separated reasoning tokens.
- Reasoning tokens ARE exposed via usage.completion_tokens_details.reasoning_tokens (Super, Ultra, Lightning) but Nano reports None; unclear whether Nano does not reason or does not report. A note in the model pages would help.
- max_tokens includes reasoning tokens; a low cap can leave no room for the visible answer (Lightning used 480/500 on a one-sentence question). Worth stating in the quickstart.

## 2026-09-30 - Nemotron 3 Super (Token Factory) tool use
- Tool calling works in standard OpenAI format, no deviations. Good.
- Model does not parallelise tool calls (one per step in our run).
- Model ignored an instruction to cite source URLs and instead emitted non-standard citation markers naming tool ids. Provenance has to be tracked in our own code.
- reasoning_tokens is exposed in usage.completion_tokens_details, which made cost logging easy. Good.

## 2026-09-30 - Nemotron 3 Super: reasoning spend and source judgment
- Reasoning tokens vary widely by step (8 to 657) when the model reconciles search results; worth surfacing in docs as expected behaviour for cost planning.
- Model treats old blog posts as "latest advisory" without checking dates; freshness must be enforced by our tools (domain pinning, dates), not by the prompt.

## 2026-10-01 - Billing / promo code clarity
- The header pill "Trial: $1.00 - 24 days" is not explained anywhere in the console; it is easy to mistake for an account or promo expiry.
- Docs disagree on whether a bank card is needed to apply a promo code (one page says billing/card setup is mandatory at onboarding, another says a promo can be applied without a card).
- Promo code emails arrive in multiple copies with different code strings and different greetings; unclear which is canonical or whether both are redeemable.

## Thu 1 Oct 2026 - NemoClaw / OpenShell / Hermes (from reading docs and issues; not yet hit ourselves)
- Search results show many unofficial NemoClaw forks, some under a NousResearch name. Hard to tell which repo is official (NVIDIA/NemoClaw). Risky for a security-focused stack.
- WSL2 tested only with Docker Desktop; native Docker Engine inside WSL is not mentioned.
- Open issues seen: onboard forces --gpu on WSL2 when nvidia-smi exists (#208, v0.0.7); install.sh may not auto-install OpenShell on WSL2 (#3989). Both old, current status unknown.
- Hermes install exists in two URL variants (raw GitHub vs hermes-agent.nousresearch.com); official docs prefer the nousresearch.com one.
- NemoClaw docs: the quickstart pipes nvidia.com/nemoclaw.sh to bash and defaults to the moving tag lkg. I found no published checksum for the bootstrap script in the pages I read; had to download and hash it myself. lkg is a lightweight tag while releases are annotated, so comparing hashes needs ls-remote without --refs plus the ^{} lines.
- NemoClaw prerequisites page lists Node 22.19+, while a third-party page (Ollama docs) says Node 20+; easy to be misled.
- nemohermes uninstall (v0.0.124) after an install with --defer-onboarding (no gateway ever registered): it stopped at step 2/6 with "Could not remove gateway registration 'nemoclaw': openshell gateway remove failed (exit 1)" and "Uninstall completed with errors". openshell gateway list reported "No gateways found". Because it halted there, steps 3-6 (Docker, ~/.nemoclaw, global CLI) did not run; cause is inferred from symptoms, not confirmed. Expected: a missing gateway should count as already removed, like the providers and sandboxes did.
- Install side effects are spread over several places (~/.local/bin shims, ~/.npm-global, ~/.npmrc prefix, ~/.bashrc PATH lines, systemd user service, ~/.nemoclaw); a single list of what the installer touches would help manual cleanup.
- The Express prompt appears even when --defer-onboarding is passed, although onboarding is then skipped.
- NemoClaw host probe on Windows/WSL reports GPU findings (toolkit, CDI) as blocking even though a remote-inference setup never needs a GPU; the CPU-only waiver exists only in the onboarding policy text, not in the probe output.
- Docker Desktop install docs say WSL 2.6+ bundles kernel 6.6, but WSL 2.7.12 ships 6.18 by default; Docker has open issues (#391, #397) about 6.18 and no published kernel compatibility matrix.
- NemoClaw is documented as tested on Windows only through Docker Desktop or rootless Podman, while native Linux Docker is the primary path; a Windows developer using native Docker Engine inside WSL only learns this from the probe.
- NemoClaw installer adds its PATH lines only to ~/.bashrc; a WSL shell opened from PowerShell/Windows Terminal as a login shell (no ~/.profile or ~/.bash_profile on Ubuntu 24.04) reports "nemohermes: command not found" until ~/.bashrc is sourced.
- nemohermes host probe reports "inconclusive" because the read-only probe never runs the WSL GPU proof, even when the only remaining finding is a warning; a CPU-only user cannot get a "supported" status from the probe.
- Docker Desktop v4.93.0 starts fine on stock WSL 2.7.12 (kernel 6.18.33); worth stating in Docker's WSL docs since they still mention kernel 6.6.
- nemohermes onboard prints 9 warnings "failed to detach provider ... sandbox not found" when creating a new sandbox; harmless but alarming on a first run.
- Onboarding says host port 8642 is held by a listener NemoClaw cannot attribute, yet the API answers there and openshell forward list shows "No active forwards"; the message and the state disagree.
- Hermes API baseline overhead is not documented: a one-word prompt used 16,715 prompt tokens (about $0.005 per call at listed prices). A note on baseline tokens per call would help budget planning.
- Restricted policy tier is described as "no tier defaults", but the live policy still includes nousresearch.com GET/POST /** and integrate.api.nvidia.com rules from the Hermes baseline; the docs could list the baseline per agent next to the tier table.
- Docs say sandbox build typically takes 5-15 minutes; it took about 100 s here.
- Hermes first-run tip says a "legacy OpenClaw directory" was detected at ~/.openclaw/, but the directory in the sandbox was created at onboarding time (05:37 UTC); migrate/cleanup advice does not apply to a fresh sandbox.
- nemohermes launch refused to start ("final validation failed due to health") because the 8642 forward is not recognized, while the API itself answers; fix was to stop the forward process and run recover. openshell forward list showed "No active forwards" although two "forward service" processes were running (bound to 0.0.0.0 inside WSL).
- Hermes log: "Tirith security scanner enabled but not available", SQLite 3.46.1 flagged as vulnerable (WAL-reset bug) with advice to run hermes update, and a lock file under /sandbox/.hermes that could not be opened although that path is in the policy's read-write list.
- Landlock log reports rules_applied:14 skipped:3 under BestEffort without naming the skipped paths; naming them would help security reviewers.
- OpenShell TUI labels an operator-pressed approval "auto-approved"; the gateway log lines (ApproveDraftChunk, CONFIG:APPROVED, RejectDraftChunk) do not name the approver, and the rejection lines do not name the host. For a security product the audit trail should say who decided and about what.
- Hermes calls POST /api/show on inference.local (an Ollama-style model-info lookup) and the managed inference policy denies it at every session start; the Hermes status bar showed "ctx --". Consider allowing it or documenting the effect.
- Hermes startup runs uv and downloads about a dozen packages from PyPI inside the sandbox and fetches a model catalog from hermes-agent.nousresearch.com; the quickstart does not mention runtime installs, which matters for network-policy planning.
- The pending-rule review shows "65% review required" and "no additional risk detected" without explaining the score.
- Hermes memory tool call from nemotron-3-super failed with "Unknown action 'None'. Use: add, replace, remove" (missing action parameter): a concrete case of the empty model-compatibility registry listed on NVIDIA's Hermes platform page.
- Hermes reported a memory file path that does not exist (profiles/default/memories/user.json); the real file is /sandbox/.hermes/memories/USER.md. The agent's self-reported storage location should not be trusted; docs could state the real path.
- Raw prompts and sessions are stored in plain text in /sandbox/.hermes/.hermes_history and runtime/state.db; memory scope vs. history scope is not explained in the quickstart, which matters for "data under user control" claims.

## Fri 2 Oct 2026 — Serverless AI / AI Cloud onboarding
- For a builder arriving from Token Factory, nothing we saw there says that Serverless Endpoints/Jobs live in a separate product (Nebius AI Cloud) with its own console, project and billing. We found out only at the "Add billing details" form, which charges the card $25 on submit.
- The Token Factory balance ($29.50 builder credit) does not visibly apply to AI Cloud. Not stated clearly where we looked. A short note in the hackathon resources would help solo builders who want to try the encouraged Serverless services.
- Docs examples use region eu-north1; our default AI Cloud project is in eu-west2. Impact on preset availability unverified.

## Fri 2 Oct 2026 — Token Factory console, Tavily, LangSmith
- Token Factory Usage: cannot group or filter by API key (only Project, Region, Label), so the spend of an agent gateway key cannot be told apart from our scripts. The default "Rounded numbers" shows "< 0.01" for small rows; "Full numbers" exists but is easy to miss. The headline total adds VAT, which makes it differ from subtotal-based estimates.
- Token Factory Prices: filtering by "Nemotron" lists old Llama-3.1-Nemotron models first, and "Cosmos3-Super-Reasoner" sits next to "Nemotron-3-Super". Easy to read the wrong row. Model IDs in the API (nvidia/nemotron-3-super-120b-a12b) differ in spelling from the price rows (Nvidia-Nemotron-3-Super-120B-A12B).
- Tavily: the $25 builder credit appears only on the Overview page (Add-on 0/3,125 credits). The Billing page shows just Researcher 0/1000 and Pay-as-you-go disabled, and the credit email does not say where to look.
- LangSmith: the $100 builder credit is invisible until a card is added; the free plan button reads "Add card to remove trace limit". wrap_openai labels every call ChatOpenAI even when the model is Nemotron on Token Factory, and no cost is shown for it.

## 2026-10-02 - Sandboxes (ConTree) friction, Day 3
1. Welcome email quickstart: the apt-get update / install example, copied as written (contree-sdk 0.3.6), prints nothing. apt install fails in a separate run (exit 100, "Unable to locate package qrencode") because run() is disposable by default. Fix: disposable=False and call .run() on the returned image. Suggest updating the email and console quickstart.
2. Opposite defaults: SDK run() is disposable by default, CLI `contree run` persists by default. Easy to lose state or save state by accident when moving between the two.
3. Env var names differ: SDK reads NEBIUS_PROJECT_ID; CLI `contree auth` reads CONTREE_PROJECT or NEBIUS_AI_PROJECT. The token is NEBIUS_API_KEY in both. After `contree auth`, CLI runtime commands read only the saved profile, not the environment. Positive: the email confirms the SDK variable names.
4. In the quickstart the variable is called "sandbox" but the object is an image (a saved filesystem state). The docs say "image"; consistent naming would help beginners.
5. `contree session show` hides the BRANCHES column on a narrow terminal (warning suggests --format json). Consider a compact branch marker in narrow mode.
6. Security note: `contree auth` stores the token in plain text in ~/.config/contree/auth.ini (mode 600 here). Fine, but worth stating in the docs.
