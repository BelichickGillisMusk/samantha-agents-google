# Samantha Agent — Build & Deploy Info

> **GCP Project ID:** `samantha-493919`  
> **Cloud Run Service:** `samantha`  
> **Region:** `us-central1`

---

## Overview

Samantha is a conversational AI agent built with Vertex AI / Gemini and deployed on Cloud Run. This document covers everything you need to build, test, and deploy Samantha from a machine **outside** of Google Cloud.

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

Copy the root `.env.example` and set these Samantha-specific values:

```dotenv
GOOGLE_CLOUD_PROJECT=samantha-493919
GOOGLE_CLOUD_REGION=us-central1
AR_REGISTRY=us-central1-docker.pkg.dev
AR_REPOSITORY=agents
CLOUD_RUN_SERVICE=samantha
VERTEX_AI_REGION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro
AGENT_BASE_URL=https://samantha-<hash>-uc.a.run.app
```

---

## Build

### Container image

```bash
# From the repo root (or the samantha service source directory)
IMAGE="us-central1-docker.pkg.dev/samantha-493919/agents/samantha:$(git rev-parse --short HEAD)"

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
  -e SAMANTHA_APP_KEY \
  -e GOOGLE_APPLICATION_CREDENTIALS \
  -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/sa.json:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/sa.json \
  "$IMAGE"
```

The agent is available at <http://localhost:8080>.

---

## Deploy to Cloud Run

```bash
gcloud run deploy samantha \
  --project=samantha-493919 \
  --region=us-central1 \
  --image="$IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=samantha-493919,VERTEX_AI_MODEL=gemini-1.5-pro" \
  --set-secrets="SAMANTHA_APP_KEY=Samantha_App_Key:latest"
```

`--set-secrets` mounts the latest version of the Secret Manager secret `Samantha_App_Key` (mixed case — Secret Manager names are case-sensitive and this one mirrors the GitHub Actions secret naming) as the env var `SAMANTHA_APP_KEY` inside the container (all caps — Linux env-var convention; container code reads `SAMANTHA_APP_KEY`). The Cloud Run service account needs `roles/secretmanager.secretAccessor` on that secret.

### Rollback to a previous revision

```bash
# List revisions
gcloud run revisions list --service=samantha --project=samantha-493919 --region=us-central1

# Roll traffic back to a specific revision
gcloud run services update-traffic samantha \
  --project=samantha-493919 \
  --region=us-central1 \
  --to-revisions=samantha-00010-abc=100
```

---

## Secrets

Samantha reads secrets from **Secret Manager**. Add or update a secret:

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

### `Samantha_App_Key` — the Google API credential

Samantha's API credential against the broad Google API surface in
`samantha-493919` lives in two places, and **the names are deliberately
different**: the **BelichickGillisMusk org-level GitHub Actions secret** named
`Samantha_App_Key` (used by CI when running the deploy pipeline) and a mirrored
copy in **Secret Manager** also named `Samantha_App_Key` (mixed case — the
case is significant; Secret Manager names are case-sensitive) in
`samantha-493919`, consumed at runtime by Cloud Run via `--set-secrets` above
and surfaced inside the container as the env var `SAMANTHA_APP_KEY` (all caps
— Linux env-var convention; container code reads the all-caps name).

The Secret Manager copy already exists. The bootstrap below is only for fresh
environments or DR; do **not** re-run it against `samantha-493919` unless you
mean to.

One-time bootstrap (run by someone who has the plaintext value — the GitHub
copy can't be read back via the API):

```bash
# Pipe the value directly so it never lands in shell history / a file.
read -rs -p "Paste Samantha_App_Key: " VALUE && echo
printf '%s' "$VALUE" | gcloud secrets create Samantha_App_Key \
  --project=samantha-493919 --replication-policy=automatic --data-file=-
unset VALUE

# Grant the Cloud Run runtime SA read access (replace SA email if you use a custom one)
SA="$(gcloud run services describe samantha --project=samantha-493919 \
  --region=us-central1 --format='value(spec.template.spec.serviceAccountName)')"
gcloud secrets add-iam-policy-binding Samantha_App_Key \
  --project=samantha-493919 \
  --member="serviceAccount:${SA:-$(gcloud projects describe samantha-493919 --format='value(projectNumber)')-compute@developer.gserviceaccount.com}" \
  --role=roles/secretmanager.secretAccessor
```

To rotate, add a new version with `gcloud secrets versions add Samantha_App_Key
--project=samantha-493919 --data-file=-` then redeploy (Cloud Run picks up the
new `:latest` on the next revision). Update the GitHub org secret separately so
CI stays in sync.

For local dev, set `SAMANTHA_APP_KEY=` in `.env` (already exposed by the
`docker run` block in [Run Locally](#run-locally)).

---

## Useful Commands

```bash
# View live logs
gcloud run services logs tail samantha \
  --project=samantha-493919 \
  --region=us-central1

# Describe the service (URL, env vars, traffic splits)
gcloud run services describe samantha \
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
2. Deploys the new image to the `samantha` Cloud Run service.
3. Runs smoke tests against the deployed URL.

To trigger a build manually:

```bash
gcloud builds triggers run samantha-deploy \
  --project=samantha-493919 \
  --region=us-central1 \
  --branch=main
```
