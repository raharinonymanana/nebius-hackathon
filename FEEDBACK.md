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
