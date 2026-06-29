# Process-Optimization Agent — Build & Deploy Info

> **GCP Project ID:** `samantha-493919` (shared — the repo runs all agents in this
> one Vertex AI project until per-agent projects are stood up; see the root README)
> **Cloud Run Service:** `process-optimization`
> **Region:** `us-central1`

> ⚠️ Do **not** use a `process-optimization-agent` project — it does not exist and
> any `gcloud`/Vertex call against it fails with GCP "Consumer invalid". Use
> `samantha-493919`, matching [`app/BUILD.md`](../../app/BUILD.md) and `chat.py`.

---

## Overview

Process-Optimization is a conversational AI agent built with Vertex AI / Gemini and
deployed on Cloud Run. It focuses on operational efficiency: analyzing workflows,
surfacing bottlenecks, and recommending concrete process improvements. This document
covers everything you need to build, test, and deploy it from a machine **outside**
of Google Cloud.

> Deploying this agent for the first time? The repo ships a Claude Code helper —
> [`/process-optimization`](../../.claude/commands/process-optimization.md) — that
> automates the repetitive scaffold/build/deploy/verify steps below and enforces the
> repo's conventions. See [`.claude/agents/process-optimization.md`](../../.claude/agents/process-optimization.md).

---

## Prerequisites

Complete the one-time steps in [SETUP.md](../../SETUP.md) first, then:

```bash
# Set the active project
gcloud config set project samantha-493919

# Confirm you are targeting the right project
gcloud config get project
```

---

## Environment Variables

Copy the root `.env.example` and set these Process-Optimization-specific values:

```dotenv
GOOGLE_CLOUD_PROJECT=samantha-493919
GOOGLE_CLOUD_REGION=us-central1
AR_REGISTRY=us-central1-docker.pkg.dev
AR_REPOSITORY=agents
CLOUD_RUN_SERVICE=process-optimization
VERTEX_AI_REGION=us-central1
VERTEX_AI_MODEL=gemini-2.5-pro
AGENT_BASE_URL=https://process-optimization-<hash>-uc.a.run.app
```

---

## Build

### Container image

```bash
# From the repo root (or the process-optimization service source directory)
IMAGE="us-central1-docker.pkg.dev/samantha-493919/agents/process-optimization:$(git rev-parse --short HEAD)"

docker build -t "$IMAGE" .
```

### Cloud Build (remote, no local Docker required)

```bash
gcloud builds submit \
  --project=samantha-493919 \
  --region=us-central1 \
  --tag="$IMAGE"
```

---

## Run Locally

```bash
# Load env vars, then start the container
source .env

docker run --rm -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT \
  -e GOOGLE_CLOUD_REGION \
  -e VERTEX_AI_MODEL \
  -e GOOGLE_APPLICATION_CREDENTIALS \
  -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/sa.json:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/sa.json \
  "$IMAGE"
```

The agent is available at <http://localhost:8080>.

---

## Deploy to Cloud Run

```bash
gcloud run deploy process-optimization \
  --project=samantha-493919 \
  --region=us-central1 \
  --image="$IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=samantha-493919,VERTEX_AI_MODEL=gemini-2.5-pro"
```

### Rollback to a previous revision

```bash
# List revisions
gcloud run revisions list --service=process-optimization --project=samantha-493919 --region=us-central1

# Roll traffic back to a specific revision
gcloud run services update-traffic process-optimization \
  --project=samantha-493919 \
  --region=us-central1 \
  --to-revisions=process-optimization-00010-abc=100
```

---

## Persona & Knowledge

This agent shares the same "single source of truth" convention as Samantha:

- **System prompt:** [`persona/system_prompt.md`](persona/system_prompt.md) — loaded as
  the system prompt for Vertex AI / Gemini. Send only the text between the
  `BEGIN`/`END SYSTEM PROMPT` markers.
- **Knowledge (RAG):** [`persona/knowledge/`](persona/knowledge/) — reference documents
  the agent grounds answers on. (The production Vertex AI Search ingestion pipeline is
  not yet documented in this repo.)

---

## Secrets

Process-Optimization reads secrets from **Secret Manager**. Add or update a secret:

```bash
# Create a new secret
echo -n "my-secret-value" | gcloud secrets create MY_SECRET_NAME \
  --project=samantha-493919 \
  --data-file=-

# Update an existing secret's value
echo -n "new-value" | gcloud secrets versions add MY_SECRET_NAME \
  --project=samantha-493919 \
  --data-file=-
```

---

## Useful Commands

```bash
# View live logs
gcloud run services logs tail process-optimization \
  --project=samantha-493919 \
  --region=us-central1

# Describe the service (URL, env vars, traffic splits)
gcloud run services describe process-optimization \
  --project=samantha-493919 \
  --region=us-central1

# List all container images
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/samantha-493919/agents \
  --project=samantha-493919
```

---

## CI/CD

Pushes to the `main` branch trigger a Cloud Build pipeline that:

1. Builds the container image and pushes it to Artifact Registry.
2. Deploys the new image to the `process-optimization` Cloud Run service.
3. Runs smoke tests against the deployed URL.

To trigger a build manually:

```bash
gcloud builds triggers run process-optimization-deploy \
  --project=samantha-493919 \
  --region=us-central1 \
  --branch=main
```
