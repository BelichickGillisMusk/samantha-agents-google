# Audra — Shared Knowledge Base (RAG)

Drop the reference documents Audra should ground her bookkeeping on into this
directory: chart of accounts, vendor categorization rules, expense policy,
invoice templates, recurring transaction patterns, tax-time checklists, etc.

This is the **single source of truth** for Audra's retrieval knowledge, used
by both backends:

- **Production (GCP):** intended to be indexed into Vertex AI Search / the
  agent's vector store. (The production ingestion pipeline is not yet
  documented in [`../../BUILD.md`](../../BUILD.md) — see that file for the rest
  of the deploy flow.)
- **Local dev:** if/when a local harness is set up, files here are uploaded
  into its document store.

## Guidelines

- **Never commit account numbers, balances, or unredacted PII.** Even an
  anonymized chart of accounts is fine; an actual general ledger export is not.
- Prefer plain text / Markdown / PDF; keep one topic per file where practical.
- Keep filenames descriptive (`chart-of-accounts.md`, `expense-categories.md`).
