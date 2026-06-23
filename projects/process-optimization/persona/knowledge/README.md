# Process-Optimization — Shared Knowledge Base (RAG)

Drop the reference documents this agent should ground its analysis on into this
directory (process maps, SOPs, runbooks, throughput/cost data, post-mortems, etc.).

- **Production (GCP):** intended to be indexed into Vertex AI Search / the agent's
  vector store. (The production ingestion pipeline is not yet documented in
  [`../../BUILD.md`](../../BUILD.md) — see that file for the rest of the deploy flow.)

## Guidelines

- **Never commit secrets or unredacted PII.** Redact anything sensitive before adding
  it here — this repo is editable from outside GCP.
- Prefer plain text / Markdown / PDF; keep one topic per file where practical.
- Keep filenames descriptive (`onboarding-sop.md`, not `doc1.pdf`).
