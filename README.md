# samantha-agents-google

Build information and configuration for Google Cloud–hosted agents used by **bryanoneillgillis.com** and related services.

All information here is intended for editing and building these projects from **outside** of Google Cloud while still targeting the project resources.

---

## Projects

| Agent | GCP Project | Status | Docs |
|-------|------------|--------|------|
| Samantha | `samantha-agent` | Active | [Build Info](projects/samantha/BUILD.md) |
| Nora | `nora-agent` | Active | [Build Info](projects/nora/BUILD.md) |
| Sloane | `sloane-agent` | Active | [Build Info](projects/sloane/BUILD.md) |

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
└── projects/
    ├── samantha/
    │   └── BUILD.md     ← Samantha agent build & deploy info
    ├── nora/
    │   └── BUILD.md     ← Nora agent build & deploy info
    └── sloane/
        └── BUILD.md     ← Sloane agent build & deploy info
```
