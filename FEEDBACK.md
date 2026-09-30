## 2026-09-30 Token Factory
- Model IDs mix casing/naming styles (NVIDIA-Nemotron-3-Nano-30B-A3B vs nemotron-3-super-120b-a12b vs Nemotron-3_5-Lightning). Easy to mistype; a consistent slug convention would help.
- Output token counts can far exceed visible reply length (Lightning: 408 tokens for one sentence); would help if the usage object clearly separated reasoning tokens.
- Reasoning tokens ARE exposed via usage.completion_tokens_details.reasoning_tokens (Super, Ultra, Lightning) but Nano reports None; unclear whether Nano does not reason or does not report. A note in the model pages would help.
- max_tokens includes reasoning tokens; a low cap can leave no room for the visible answer (Lightning used 480/500 on a one-sentence question). Worth stating in the quickstart.
