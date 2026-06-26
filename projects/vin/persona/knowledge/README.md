# Vin — Shared Knowledge Base (RAG)

Drop the reference documents Vin should ground his infra decisions on into
this directory: Cloudflare account map (Workers ↔ routes ↔ domains), GitHub
repo inventory, deploy runbooks, branch / merge conventions, secrets rotation
schedules, DNS records, R2 bucket purposes, etc.

This is the **single source of truth** for Vin's retrieval knowledge, used by
both backends:

- **Production (GCP):** intended to be indexed into Vertex AI Search / the
  agent's vector store. (The production ingestion pipeline is not yet
  documented in [`../../BUILD.md`](../../BUILD.md) — see that file for the rest
  of the deploy flow.)
- **Local dev:** if/when a local harness is set up, files here are uploaded
  into its document store.

## Guidelines

- **Never commit secrets, API tokens, deploy keys, or webhook URLs.** Redact
  everything. The Cloudflare API token and GitHub PAT live in Secret Manager
  (see [`../BUILD.md`](../BUILD.md)) — not here.
- Prefer plain text / Markdown / PDF; keep one topic per file where practical.
- Keep filenames descriptive (`cloudflare-workers-map.md`,
  `github-repo-inventory.md`, `deploy-runbook.md`).
