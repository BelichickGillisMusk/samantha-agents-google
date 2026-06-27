# Sloane — Shared Knowledge Base (RAG)

Drop the reference documents Sloane should ground her copy on into this
directory: brand voice & style guide, approved taglines, service descriptions,
client testimonials, banned-phrase list, past campaigns, tone examples, etc.

This is the **single source of truth** for Sloane's retrieval knowledge, used
by both backends:

- **Production (GCP):** intended to be indexed into Vertex AI Search / the
  agent's vector store. (The production ingestion pipeline is not yet
  documented in [`../../BUILD.md`](../../BUILD.md) — see that file for the rest
  of the deploy flow.)
- **Local dev:** if/when a local harness is set up, files here are uploaded
  into its document store.

## Guidelines

- **Never commit secrets or unredacted client info.** Anonymize testimonials
  and remove anything sensitive before adding it here.
- Prefer plain text / Markdown / PDF; keep one topic per file where practical.
- Keep filenames descriptive (`brand-voice.md`, `approved-taglines.md`).
