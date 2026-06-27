# Nora — Shared Knowledge Base (RAG)

Drop the reference documents Nora should ground her answers on into this
directory: runbooks for our sites, Make.com scenario inventories, lead-intake
flow diagrams, alert/escalation contacts, status-page conventions, etc.

This is the **single source of truth** for Nora's retrieval knowledge, used by
both backends:

- **Production (GCP):** intended to be indexed into Vertex AI Search / the
  agent's vector store. (The production ingestion pipeline is not yet
  documented in [`../../BUILD.md`](../../BUILD.md) — see that file for the rest
  of the deploy flow.)
- **Local dev:** if/when a local harness is set up, files here are uploaded
  into its document store.

## Guidelines

- **Never commit secrets or unredacted PII.** Redact API keys, webhook URLs,
  and personal info before adding anything here.
- Prefer plain text / Markdown / PDF; keep one topic per file where practical.
- Keep filenames descriptive (`make-scenarios.md`, `intake-flow.md`).
