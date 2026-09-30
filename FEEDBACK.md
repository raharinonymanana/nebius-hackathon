## 2026-09-30 Token Factory
- Model IDs mix casing/naming styles (NVIDIA-Nemotron-3-Nano-30B-A3B vs nemotron-3-super-120b-a12b vs Nemotron-3_5-Lightning). Easy to mistype; a consistent slug convention would help.
- Output token counts can far exceed visible reply length (Lightning: 408 tokens for one sentence); would help if the usage object clearly separated reasoning tokens.
