# SAM custom build for the prove-it demo Lambda (template.yaml:
# DemoFunction Metadata.BuildMethod: makefile).
#
# CodeUri is the repo root, but we do NOT ship the repo. This target copies an
# explicit, auditable per-file ALLOWLIST into $(ARTIFACTS_DIR), preserving the
# prover/ + targets/ sibling layout that prover/verify_service.py relies on
# (it resolves targets/ormar/spec.py as dirname(dirname(verify_service.py))/
# targets/ormar/spec.py), then pip-installs ONLY contree-sdk into the same dir.
#
# Deliberately NOT copied: .env, receipts/, frontend/, LOG/DECISIONS/FEEDBACK/
# README, usage_log.jsonl, samconfig.toml, root requirements.txt, and every
# prover/ or targets/ file other than the four named below.

build-DemoFunction:
	# --- handler + static assets (from demo/, flattened to bundle root) ---
	cp demo/app.py          "$(ARTIFACTS_DIR)/app.py"
	cp demo/demo_data.json  "$(ARTIFACTS_DIR)/demo_data.json"
	mkdir -p "$(ARTIFACTS_DIR)/web"
	cp -r demo/web/.        "$(ARTIFACTS_DIR)/web/"
	# --- prover package: ONLY the empty __init__ + the verify service ---
	mkdir -p "$(ARTIFACTS_DIR)/prover"
	cp prover/__init__.py       "$(ARTIFACTS_DIR)/prover/__init__.py"
	cp prover/verify_service.py "$(ARTIFACTS_DIR)/prover/verify_service.py"
	# --- ormar cartridge: ONLY spec.py (imported) + adapter.py (read at run) ---
	mkdir -p "$(ARTIFACTS_DIR)/targets/ormar"
	cp targets/ormar/spec.py    "$(ARTIFACTS_DIR)/targets/ormar/spec.py"
	cp targets/ormar/adapter.py "$(ARTIFACTS_DIR)/targets/ormar/adapter.py"
	# --- third-party dep: ONLY the ConTree SDK (pulls aiofiles, cattrs, httpx,
	#     strenum, typing-extensions). boto3 is provided by the Lambda runtime. ---
	pip install contree-sdk==0.3.6 -t "$(ARTIFACTS_DIR)"
