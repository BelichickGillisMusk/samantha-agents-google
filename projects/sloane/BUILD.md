# Sloane Agent — Build & Deploy Info

> **GCP Project ID:** `sloane-agent`  
> **Cloud Run Service:** `sloane`  
> **Region:** `us-central1`

---

## Overview

Sloane is a conversational AI agent built with Vertex AI / Gemini and deployed on Cloud Run. This document covers everything you need to build, test, and deploy Sloane from a machine **outside** of Google Cloud.

---

## Prerequisites

Complete the one-time steps in [SETUP.md](../../SETUP.md) first, then:

```bash
# Set the active project
gcloud config set project sloane-agent

# Confirm you are targeting the right project
gcloud config get project
```

---

## Environment Variables

Copy the root `.env.example` and set these Sloane-specific values:

```dotenv
GOOGLE_CLOUD_PROJECT=sloane-agent
GOOGLE_CLOUD_REGION=us-central1
AR_REGISTRY=us-central1-docker.pkg.dev
AR_REPOSITORY=agents
CLOUD_RUN_SERVICE=sloane
VERTEX_AI_REGION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro
AGENT_BASE_URL=https://sloane-<hash>-uc.a.run.app
```

---

## Build

### Container image

```bash
IMAGE="us-central1-docker.pkg.dev/sloane-agent/agents/sloane:$(git rev-parse --short HEAD)"

docker build -t "$IMAGE" .
```

### Cloud Build (remote, no local Docker required)

```bash
gcloud builds submit \
  --project=sloane-agent \
  --region=us-central1 \
  --tag="$IMAGE"
```

---

## Run Locally

```bash
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
gcloud run deploy sloane \
  --project=sloane-agent \
  --region=us-central1 \
  --image="$IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=sloane-agent,VERTEX_AI_MODEL=gemini-1.5-pro"
```

### Rollback to a previous revision

```bash
# List revisions
gcloud run revisions list --service=sloane --project=sloane-agent --region=us-central1

# Roll traffic back to a specific revision
gcloud run services update-traffic sloane \
  --project=sloane-agent \
  --region=us-central1 \
  --to-revisions=sloane-00010-abc=100
```

---

## Secrets

Sloane reads secrets from **Secret Manager**. Add or update a secret:

```bash
# Create a new secret
echo -n "my-secret-value" | gcloud secrets create MY_SECRET_NAME \
  --project=sloane-agent \
  --data-file=-

# Update an existing secret's value
echo -n "new-value" | gcloud secrets versions add MY_SECRET_NAME \
  --project=sloane-agent \
  --data-file=-
```

---

## Useful Commands

```bash
# View live logs
gcloud run services logs tail sloane \
  --project=sloane-agent \
  --region=us-central1

# Describe the service (URL, env vars, traffic splits)
gcloud run services describe sloane \
  --project=sloane-agent \
  --region=us-central1

# List all container images
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/sloane-agent/agents \
  --project=sloane-agent
```

---

## CI/CD

Pushes to the `main` branch trigger a Cloud Build pipeline that:

1. Builds the container image and pushes it to Artifact Registry.
2. Deploys the new image to the `sloane` Cloud Run service.
3. Runs smoke tests against the deployed URL.

To trigger a build manually:

```bash
gcloud builds triggers run sloane-deploy \
  --project=sloane-agent \
  --region=us-central1 \
  --branch=main
```
