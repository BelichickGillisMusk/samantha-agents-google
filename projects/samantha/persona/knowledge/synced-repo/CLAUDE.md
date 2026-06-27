<!-- source: this repo's CLAUDE.md -->
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **docs + configuration repo** (no application source code) for Google Cloud–hosted conversational agents that power **bryanoneillgillis.com** and related services. Each agent — Samantha, Nora, Sloane, Process-Optimization — gets its own GCP project, Cloud Run service, and Vertex AI / Gemini model. Everything here is for editing/building those projects from **outside** Google Cloud while targeting the project resources.

There is no test suite, lint config, build script, or package manifest at the repo root. "Building" means `docker build` + `gcloud run deploy` per agent; "testing" means smoke-testing the deployed Cloud Run URL or iterating locally against the Ollama harness.

## Repo conventions (enforced for every agent)

Every agent under `projects/<name>/` follows the **same** pattern. Mirror it exactly when adding or editing one:

- **GCP project:** `<name>-agent` · **Cloud Run service / image name:** `<name>` · **Region:** `us-central1`
  - **Samantha is the documented exception:** her project ID is `samantha-493919` (a legacy ID predating the convention), not `samantha-agent`. New agents still follow `<name>-agent`.
- **Artifact Registry repo:** `agents` (host `us-central1-docker.pkg.dev`)
- **Model:** `gemini-2.5-pro` via Vertex AI
- **Files:** `projects/<name>/BUILD.md`, `projects/<name>/persona/system_prompt.md`, `projects/<name>/persona/knowledge/README.md`
- **Persona file:** the prompt MUST sit between `<!-- BEGIN SYSTEM PROMPT -->` and `<!-- END SYSTEM PROMPT -->` markers. Production reads only the text between those markers.
- **README.md** has a roster table and a repository-structure block — add a row + entry for any new agent.

Image tags in any added `docker-compose.yml` are **pinned** (no `:latest`/`:main`) for reproducibility.

## Adding a new agent

Use the `/process-optimization` slash command (`.claude/commands/process-optimization.md`), which delegates to the `process-optimization` subagent (`.claude/agents/process-optimization.md`). It scaffolds `BUILD.md` + persona files from the Samantha template, wires the README roster row, and opens a **draft** PR (never enables auto-merge). Don't touch GCP (`gcloud builds submit`, `gcloud run deploy`) unless the user explicitly authorizes it.

## Persona = single source of truth (production + local)

Samantha is the only agent with a local dev harness today (`projects/samantha/docker-compose.yml` → Ollama + Open WebUI on `127.0.0.1:3000`). The harness intentionally shares two artifacts with production so behavior doesn't drift:

| Artifact | Production (GCP) | Local (Ollama/Open WebUI) |
|---|---|---|
| `persona/system_prompt.md` | System prompt for Gemini | Pasted into Open WebUI Modelfile |
| `persona/knowledge/` | Intended for Vertex AI Search (ingestion not yet documented in this repo) | Uploaded as Open WebUI Documents for RAG |

Edit those files **once**; both backends pick them up. The local model is open-weight (Llama 3 / Mistral), **not** Gemini — use the harness for persona/RAG/UX iteration, not to validate production output. `ollama run samantha` pulls an unrelated community model that shares the name; ignore it and start from `llama3` + our system prompt.

## Common commands

One-time tooling/auth lives in [SETUP.md](SETUP.md). Per-agent commands live in each `projects/<name>/BUILD.md`. The shapes that recur:

```bash
# Switch active project (one per agent)
gcloud config set project <name>-agent

# Build + push image (tag = short SHA for traceability)
IMAGE="us-central1-docker.pkg.dev/<name>-agent/agents/<name>:$(git rev-parse --short HEAD)"
gcloud builds submit --project=<name>-agent --region=us-central1 --tag="$IMAGE"

# Deploy to Cloud Run
gcloud run deploy <name> --project=<name>-agent --region=us-central1 \
  --image="$IMAGE" --platform=managed --allow-unauthenticated --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=<name>-agent,VERTEX_AI_MODEL=gemini-2.5-pro"

# Tail logs / describe service
gcloud run services logs tail <name> --project=<name>-agent --region=us-central1
gcloud run services describe <name> --project=<name>-agent --region=us-central1

# Rollback: list revisions, then split traffic to a known-good one
gcloud run revisions list --service=<name> --project=<name>-agent --region=us-central1
gcloud run services update-traffic <name> --project=<name>-agent --region=us-central1 \
  --to-revisions=<name>-00010-abc=100
```

Samantha local harness only:

```bash
# From projects/samantha/  (WEBUI_SECRET_KEY must be set in repo-root .env)
docker compose --env-file ../../.env up -d         # start
docker compose down                                 # stop, keep data
docker compose down -v && rm -rf ollama open-webui  # full reset
```

## Env vars

The root `.env.example` is a **Markdown file with a fenced dotenv block** — `cp .env.example .env` then strip the markdown wrapper, or copy just the dotenv contents. Required keys cluster around: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, `AR_REGISTRY`, `AR_REPOSITORY`, `CLOUD_RUN_SERVICE`, `VERTEX_AI_REGION`, `VERTEX_AI_MODEL`, `AGENT_BASE_URL`. `WEBUI_SECRET_KEY` is only for the Samantha local harness — generate with `openssl rand -hex 32` and make sure the final `.env` has **exactly one** `WEBUI_SECRET_KEY=` assignment (loader behavior on duplicates varies: some take the first, docker-compose's env_file takes the last — don't rely on either).

Production secrets go through **Secret Manager** (`gcloud secrets create / versions add`), never `.env` or the repo. Samantha's Google API credential is the canonical example, and the **same value lives under three differently-cased names** across systems — don't try to "normalize" them:

- **GitHub Actions org secret** (BelichickGillisMusk, public-repo scope): `SAMANTHA_APP_KEY` (all-caps; write-only via the GitHub API). A `SAMANTHA` secret also exists scoped to private repos — verify separately before assuming it's the same value.
- **GCP Secret Manager** (in `samantha-493919`): `Samantha_App_Key` (mixed case; Secret Manager is case-sensitive).
- **Container env var**: `SAMANTHA_APP_KEY` (all-caps Linux env-var convention).

Injected at runtime via `gcloud run deploy ... --set-secrets="SAMANTHA_APP_KEY=Samantha_App_Key:latest"`. See [`projects/samantha/BUILD.md`](projects/samantha/BUILD.md#samantha_app_key--the-google-api-credential) for the bootstrap and rotation steps.

## CI/CD

The real per-agent pipeline is the **Cloud Build trigger** named `<name>-deploy` documented in each agent's `BUILD.md` — it runs on pushes to `main` and does build image → deploy → smoke-test the Cloud Run URL. The two files under `.github/workflows/` are **not** the real pipeline: `google.yml` is the unmodified GKE sample (placeholders `PROJECT_ID: my-project`, `REPOSITORY: samples`, GKE deploy steps) and `blank.yml` is a Hello World stub. Leave them alone or replace them deliberately — don't treat them as canonical. Manual trigger of the Cloud Build path:

```bash
gcloud builds triggers run <name>-deploy --project=<name>-agent --region=us-central1 --branch=main
```

## Guardrails when editing

- **Don't claim pipelines exist that aren't documented** (e.g. the Vertex AI Search ingestion path for `persona/knowledge/`). Mirror the repo's deliberately honest wording.
- **Don't invent BUILD.md steps** not present in the existing agents — they're meant to be uniform.
- When scaffolding a new agent (e.g. `widget`), grep its dir for **all** leftover template tokens before committing — not just its own name: `grep -rE "samantha|nora|sloane|<name>|<hash>" projects/widget` (extend the alternation with any other agent names already in the repo).
- Keep changes scoped to the agent being touched; don't refactor unrelated files.
