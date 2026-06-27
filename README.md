# samantha-agents-google

Build information and configuration for Google Cloud–hosted agents used by **bryanoneillgillis.com** and related services.

All information here is intended for editing and building these projects from **outside** of Google Cloud while still targeting the project resources.

---

## Projects

| Agent | GCP Project | Status | Docs |
|-------|------------|--------|------|
| **Samantha** — Google APIs (Gmail / Calendar / Drive) | `samantha-493919` (legacy ID — does **not** follow the `<name>-agent` convention) | Active | [Cheatsheet](projects/samantha/CHEATSHEET.md) · [Build Info](projects/samantha/BUILD.md) · [Local Dev](projects/samantha/LOCAL_DEV.md) |
| **Nora** — Ops (website / Make.com / lead intake) | `nora-agent` | Persona live, deploy pending | [Build Info](projects/nora/BUILD.md) |
| **Sloane** — Content & brand voice | `sloane-agent` | Persona live, deploy pending | [Build Info](projects/sloane/BUILD.md) |
| **Audra** — Accounting & bookkeeping | `audra-agent` | Persona live, deploy pending | [Build Info](projects/audra/BUILD.md) |
| **Vin** — Site infra (Cloudflare + GitHub) | `vin-agent` | Persona live, deploy + connectors pending | [Build Info](projects/vin/BUILD.md) |
| Process-Optimization | `process-optimization-agent` | Active (meta-agent — scaffolds new agents) | [Build Info](projects/process-optimization/BUILD.md) |

**Talk to any of the five right now** (no deploy needed): `./projects/samantha/chat.py --agent <samantha\|nora\|sloane\|audra\|vin>` from the repo root. Same CLI, five personas, one shared Vertex AI project (`samantha-493919`) until per-agent projects are stood up.

**Web / mobile app**: [`app/`](app/BUILD.md) — Cloud Run + FastAPI backend that fronts all five agents; single-page PWA frontend (installable to phone home screen). Backed by the same persona files + Vertex AI Gemini 2.5 Pro. See [`app/BUILD.md`](app/BUILD.md) for build + deploy.

> **Deploying a new agent?** Use the [`/process-optimization`](.claude/commands/process-optimization.md)
> Claude Code agent — it scaffolds, configures, and submits a new agent following the
> conventions above. See [`.claude/agents/process-optimization.md`](.claude/agents/process-optimization.md).

---

## Quick Start (external / local development)

1. **Install required tooling** — see [SETUP.md](SETUP.md)
2. **Copy and configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your project-specific values
   ```
3. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
4. Navigate to the relevant project folder under `projects/` and follow its `BUILD.md`.

---

## Repository Structure

```
samantha-agents-google/
├── README.md            ← This file
├── SETUP.md             ← One-time tooling & auth setup guide
├── .env.example         ← Template for environment variables
├── .claude/
│   ├── agents/
│   │   └── process-optimization.md   ← Agent that deploys new agents
│   └── commands/
│       └── process-optimization.md   ← /process-optimization slash command
└── projects/
    ├── samantha/
    │   ├── BUILD.md            ← Samantha agent build & deploy info (GCP)
    │   ├── LOCAL_DEV.md        ← Local Ollama + Open WebUI dev harness
    │   ├── docker-compose.yml  ← Local dev stack (not production)
    │   └── persona/            ← Shared system prompt + RAG docs (both backends)
    ├── nora/
    │   └── BUILD.md     ← Nora agent build & deploy info
    ├── sloane/
    │   └── BUILD.md     ← Sloane agent build & deploy info
    └── process-optimization/
        ├── BUILD.md     ← Process-Optimization agent build & deploy info
        └── persona/     ← System prompt + RAG docs
```
