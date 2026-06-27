# Audra Agent — Build & Deploy Info

> **GCP Project ID:** `audra-agent`
> **Cloud Run Service:** `audra`
> **Region:** `us-central1`

---

## Overview

Audra is the Accounting & Bookkeeping conversational agent — drafts invoices,
categorizes expenses, flags anomalies, helps prepare for monthly close. Built
with Vertex AI / Gemini, deployed on Cloud Run, follows the same `<name>-agent`
convention as Nora and Sloane.

> **Talk to her right now without deploying:**
> `./projects/samantha/chat.py --agent audra` (from the repo root). Same CLI
> handles all four agents; see [`../samantha/BUILD.md`](../samantha/BUILD.md)
> for the script details.

---

## Prerequisites

Complete the one-time steps in [SETUP.md](../../SETUP.md) first, then:

```bash
gcloud config set project audra-agent
gcloud config get project
```

---

## Environment Variables

Copy the root `.env.example` and set these Audra-specific values:

```dotenv
GOOGLE_CLOUD_PROJECT=audra-agent
GOOGLE_CLOUD_REGION=us-central1
AR_REGISTRY=us-central1-docker.pkg.dev
AR_REPOSITORY=agents
CLOUD_RUN_SERVICE=audra
VERTEX_AI_REGION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro
AGENT_BASE_URL=https://audra-<hash>-uc.a.run.app
```

---

## Build

```bash
IMAGE="us-central1-docker.pkg.dev/audra-agent/agents/audra:$(git rev-parse --short HEAD)"
gcloud builds submit --project=audra-agent --region=us-central1 --tag="$IMAGE"
```

---

## Deploy to Cloud Run

```bash
gcloud run deploy audra \
  --project=audra-agent \
  --region=us-central1 \
  --image="$IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=audra-agent,VERTEX_AI_MODEL=gemini-1.5-pro"
```

### Rollback to a previous revision

```bash
gcloud run revisions list --service=audra --project=audra-agent --region=us-central1
gcloud run services update-traffic audra \
  --project=audra-agent --region=us-central1 \
  --to-revisions=audra-00010-abc=100
```

---

## Persona & Knowledge

Same "single source of truth" convention as the other agents:

- **System prompt:** [`persona/system_prompt.md`](persona/system_prompt.md) —
  send only the text between the `BEGIN`/`END SYSTEM PROMPT` markers.
- **Knowledge (RAG):** [`persona/knowledge/`](persona/knowledge/) — chart of
  accounts, vendor rules, expense policy. (Production Vertex AI Search
  ingestion is not yet documented in this repo.)

---

## Secrets

Audra reads secrets from **Secret Manager** in `audra-agent`. Standard pattern:

```bash
echo -n "value" | gcloud secrets create MY_SECRET_NAME \
  --project=audra-agent --data-file=-
```

If Audra needs a credential to talk to QuickBooks / Stripe / a bank-feed
provider, follow the same wiring Samantha uses for `SAMANTHA_APP_KEY`
([`../samantha/BUILD.md`](../samantha/BUILD.md#samantha_app_key--the-google-api-credential)):
GitHub Actions secret → Secret Manager → `--set-secrets=` on `gcloud run
deploy`.

---

## Useful Commands

```bash
gcloud run services logs tail audra --project=audra-agent --region=us-central1
gcloud run services describe audra --project=audra-agent --region=us-central1
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/audra-agent/agents --project=audra-agent
```

---

## CI/CD

Pushes to `main` trigger a Cloud Build pipeline (`audra-deploy`) that builds
the container, deploys to Cloud Run, and smoke-tests the URL. Manual trigger:

```bash
gcloud builds triggers run audra-deploy \
  --project=audra-agent --region=us-central1 --branch=main
```
