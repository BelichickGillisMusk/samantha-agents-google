# samantha-agents-google

Build information and configuration for Google Cloud–hosted agents used by **bryanoneillgillis.com** and related services.

All information here is intended for editing and building these projects from **outside** of Google Cloud while still targeting the project resources.

---

## Projects

| Agent | GCP Project | Status | Docs |
|-------|------------|--------|------|
| Samantha | `samantha-agent` | Active | [Build Info](projects/samantha/BUILD.md) · [Local Dev](projects/samantha/LOCAL_DEV.md) |
| Nora | `nora-agent` | Active | [Build Info](projects/nora/BUILD.md) |
| Sloane | `sloane-agent` | Active | [Build Info](projects/sloane/BUILD.md) |
| Process-Optimization | `process-optimization-agent` | Active | [Build Info](projects/process-optimization/BUILD.md) |

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
