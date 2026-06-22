# Samantha — Shared Knowledge Base (RAG)

Drop the reference documents Samantha should ground her answers on into this
directory (handbooks, project histories, redacted client lists, FAQs, etc.).

This is the **single source of truth** for Samantha's retrieval knowledge, used
by both backends:

- **Production (GCP):** intended to be indexed into Vertex AI Search / the
  agent's vector store. (The production ingestion pipeline is not yet documented
  in [`../../BUILD.md`](../../BUILD.md) — see that file for the rest of the
  deploy flow.)
- **Local dev (Ollama + Open WebUI):** uploaded into Open WebUI **Documents** and
  tagged in chat. See [`../../LOCAL_DEV.md`](../../LOCAL_DEV.md).

## Guidelines

- **Never commit secrets or unredacted PII.** Redact client lists and anything
  sensitive before adding it here — this repo is editable from outside GCP.
- Prefer plain text / Markdown / PDF; keep one topic per file where practical.
- Keep filenames descriptive (`refund-policy.md`, not `doc1.pdf`) — both the
  cloud index and Open WebUI surface them by name.
