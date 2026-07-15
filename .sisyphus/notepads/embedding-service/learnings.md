# Learnings - Embedding Service

## Model Dimension Discovery
- `BAAI/bge-small-zh-v1.5` outputs **512** dimensions, not 384.
- The English variant `bge-small-en-v1.5` uses MiniLM (384d), but the Chinese variant uses a small BERT (512d hidden_size).
- DIMENSION constant set to 512 to match actual model output.
