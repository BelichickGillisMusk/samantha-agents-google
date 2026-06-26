# Vin Agent — Build & Deploy Info

> **GCP Project ID:** `vin-agent`
> **Cloud Run Service:** `vin`
> **Region:** `us-central1`

---

## Overview

Vin is the Site Infrastructure agent — Cloudflare + GitHub + ship velocity.
He pairs with Nora (she monitors; he builds). Built with Vertex AI / Gemini,
deployed on Cloud Run, follows the `<name>-agent` convention.

> **Talk to him right now without deploying:**
> `./projects/samantha/chat.py --agent vin` (from the repo root). Same CLI
> handles all five agents.

---

## Prerequisites

Complete the one-time steps in [SETUP.md](../../SETUP.md) first, then:

```bash
gcloud config set project vin-agent
gcloud config get project
```

---

## Environment Variables

Copy the root `.env.example` and set these Vin-specific values:

```dotenv
GOOGLE_CLOUD_PROJECT=vin-agent
GOOGLE_CLOUD_REGION=us-central1
AR_REGISTRY=us-central1-docker.pkg.dev
AR_REPOSITORY=agents
CLOUD_RUN_SERVICE=vin
VERTEX_AI_REGION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro
AGENT_BASE_URL=https://vin-<hash>-uc.a.run.app
```

---

## Build

```bash
IMAGE="us-central1-docker.pkg.dev/vin-agent/agents/vin:$(git rev-parse --short HEAD)"
gcloud builds submit --project=vin-agent --region=us-central1 --tag="$IMAGE"
```

---

## Deploy to Cloud Run

```bash
gcloud run deploy vin \
  --project=vin-agent \
  --region=us-central1 \
  --image="$IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=vin-agent,VERTEX_AI_MODEL=gemini-1.5-pro" \
  --set-secrets="CLOUDFLARE_API_TOKEN=Cloudflare_Api_Token:latest,GITHUB_PAT=Github_Pat:latest"
```

### Rollback to a previous revision

```bash
gcloud run revisions list --service=vin --project=vin-agent --region=us-central1
gcloud run services update-traffic vin \
  --project=vin-agent --region=us-central1 \
  --to-revisions=vin-00010-abc=100
```

---

## Persona & Knowledge

Same convention as the other agents:

- **System prompt:** [`persona/system_prompt.md`](persona/system_prompt.md) —
  send only the text between the `BEGIN`/`END SYSTEM PROMPT` markers.
- **Knowledge (RAG):** [`persona/knowledge/`](persona/knowledge/) — Cloudflare
  account map, GitHub repo inventory, deploy runbooks. (Production Vertex AI
  Search ingestion is not yet documented in this repo.)

---

## Secrets — the two connectors

Vin needs two credentials to actually act on Cloudflare and GitHub. Both follow
the same GitHub-org-secret → Secret Manager → `--set-secrets` pattern that
Samantha uses for `SAMANTHA_APP_KEY` (see
[`../samantha/BUILD.md`](../samantha/BUILD.md#samantha_app_key--the-google-api-credential)).

### `Cloudflare_Api_Token`

Scope (least-privilege baseline): `Account: Workers Scripts: Read/Edit`,
`Account: Workers Routes: Read/Edit`, `Account: D1: Read/Edit` (only if used),
`Zone: DNS: Read` (or Edit if Vin should manage DNS). Create at
**dash.cloudflare.com → Profile → API Tokens → Create Token**.

```bash
read -rs -p "Paste Cloudflare API token: " VALUE && echo
printf '%s' "$VALUE" | gcloud secrets create Cloudflare_Api_Token \
  --project=vin-agent --replication-policy=automatic --data-file=-
unset VALUE
```

### `Github_Pat`

Fine-grained PAT (preferred) or classic PAT with `repo` + `workflow` scopes.
Create at **github.com → Settings → Developer settings → Personal access
tokens**. Limit to the `BelichickGillisMusk` org.

```bash
read -rs -p "Paste GitHub PAT: " VALUE && echo
printf '%s' "$VALUE" | gcloud secrets create Github_Pat \
  --project=vin-agent --replication-policy=automatic --data-file=-
unset VALUE
```

Grant the Cloud Run runtime SA `roles/secretmanager.secretAccessor` on both
secrets after creating them (same SA-lookup snippet as Samantha's BUILD.md).

---

## Tool wiring (the "connector" part — not built yet)

The persona above lets Vin **reason about** Cloudflare and GitHub; making him
actually call them requires Gemini function-calling tools in his container
code. None of that lives in this docs repo. The minimum tool set worth
shipping first:

| Tool | API | Cost to wire |
|---|---|---|
| `list_workers` | `GET /accounts/{id}/workers/scripts` | XS |
| `get_worker_routes` | `GET /zones/{zid}/workers/routes` | S |
| `deploy_worker` | `PUT /accounts/{id}/workers/scripts/{name}` | M |
| `list_repos` | `GET /orgs/{org}/repos` | XS |
| `open_pr` | `POST /repos/{owner}/{repo}/pulls` | S |
| `merge_pr` | `PUT /repos/{owner}/{repo}/pulls/{n}/merge` | S |
| `get_workflow_runs` | `GET /repos/{owner}/{repo}/actions/runs` | S |

Until those tools are wired, Vin's value is: knows the territory, drafts the
exact commands / PR descriptions / runbook entries you can paste.

---

## Useful Commands

```bash
gcloud run services logs tail vin --project=vin-agent --region=us-central1
gcloud run services describe vin --project=vin-agent --region=us-central1
```

---

## CI/CD

Pushes to `main` trigger a Cloud Build pipeline (`vin-deploy`). Manual trigger:

```bash
gcloud builds triggers run vin-deploy \
  --project=vin-agent --region=us-central1 --branch=main
```
