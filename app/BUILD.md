# Agents Web — Build & Deploy

The web app: pick an agent (Samantha / Nora / Sloane / Audra / Vin), type a
task, get a reply. Mobile-first, installable as a Progressive Web App so it
lives on your phone's home screen like a native assistant. Backed by Cloud
Run + Vertex AI Gemini 2.5 Pro in `samantha-493919`.

| | |
|---|---|
| **GCP project** | `samantha-493919` (shared with Samantha's deploy) |
| **Cloud Run service** | `agents-web` |
| **Region** | `us-central1` |
| **Image** | `us-central1-docker.pkg.dev/samantha-493919/agents/agents-web` |

---

## What's in this folder

```
app/
├── main.py                  FastAPI backend — wraps chat.py logic over HTTP
├── requirements.txt         pip deps (fastapi, uvicorn, google-auth, pydantic)
├── Dockerfile               python:3.12-slim, copies app/ + projects/
├── static/
│   ├── index.html           single-page UI with agent picker + chat thread
│   ├── manifest.webmanifest PWA manifest (installable on iOS/Android)
│   └── sw.js                minimal service worker; never caches /api/* replies
└── BUILD.md                 this file
```

The backend reuses `projects/samantha/chat.py` (`AGENTS`, `extract_persona`,
`persona_path`) — one source of truth for the persona files.

---

## Run locally (no deploy)

```bash
# from repo root
gcloud auth application-default login            # one-time

pip install -r app/requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload

# in another tab — sanity:
curl -s localhost:8080/api/agents
curl -s -X POST localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"samantha","message":"hi"}'

# open the UI:
open http://127.0.0.1:8080
```

The backend uses ADC (`gcloud auth application-default login`) locally; on
Cloud Run it uses the runtime service account automatically.

---

## Build & deploy

```bash
# from repo root — Dockerfile is at app/Dockerfile but build context is the repo
IMAGE="us-central1-docker.pkg.dev/samantha-493919/agents/agents-web:$(git rev-parse --short HEAD)"
gcloud builds submit \
  --project=samantha-493919 \
  --region=us-central1 \
  --tag="$IMAGE" \
  --config=- <<'YAML'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ["build", "-f", "app/Dockerfile", "-t", "$_IMAGE", "."]
  - name: gcr.io/cloud-builders/docker
    args: ["push", "$_IMAGE"]
images: ["$_IMAGE"]
substitutions:
  _IMAGE: "${IMAGE}"
YAML

# Simpler one-shot using the cloudbuilders default flow (also fine):
gcloud builds submit . --project=samantha-493919 --region=us-central1 \
  --config=app/cloudbuild.yaml --substitutions=_IMAGE="$IMAGE"
```

If you don't want to set up a `cloudbuild.yaml`, the `gcloud builds submit
--tag` shorthand can be used by moving the Dockerfile to repo root first; or
build locally:

```bash
docker build -f app/Dockerfile -t "$IMAGE" .
docker push "$IMAGE"
```

Deploy:

```bash
gcloud run deploy agents-web \
  --project=samantha-493919 \
  --region=us-central1 \
  --image="$IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --max-instances=10 \
  --memory=512Mi \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=samantha-493919,VERTEX_AI_MODEL=gemini-2.5-pro"
```

`--allow-unauthenticated` makes the URL public. For private access, drop that
flag and front it with **Cloud IAP** + your Workspace identity.

The deploy command returns a URL like `https://agents-web-<hash>-uc.a.run.app`
— open on your phone, then **Add to Home Screen** (Safari) / **Install app**
(Chrome). It will launch full-screen like a native app.

---

## Auth options

| | When | Setup |
|---|---|---|
| **Public** | Internal tools, behind a hard-to-guess URL | `--allow-unauthenticated` (current default) |
| **Cloud IAP** | Production / domain-mapped | Drop `--allow-unauthenticated`, attach IAP with your Workspace OAuth |
| **Firebase Auth + verify on backend** | Multi-user with sign-in screen | Add Firebase JS SDK + a FastAPI dependency that verifies the ID token |

---

## Tighten the runtime service account (recommended)

Default Cloud Run uses the project's Compute Engine default SA. For the agents
web service, grant only what it needs:

```bash
gcloud iam service-accounts create agents-web-sa \
  --project=samantha-493919 \
  --display-name="agents-web runtime"

gcloud projects add-iam-policy-binding samantha-493919 \
  --member="serviceAccount:agents-web-sa@samantha-493919.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Then redeploy with --service-account flag:
gcloud run deploy agents-web --project=samantha-493919 --region=us-central1 \
  --image="$IMAGE" \
  --service-account="agents-web-sa@samantha-493919.iam.gserviceaccount.com" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=samantha-493919,VERTEX_AI_MODEL=gemini-2.5-pro"
```

---

## What's NOT built (yet)

- **Auth** — v1 ships open. Wire IAP or Firebase before exposing publicly.
- **Persistent conversation memory** — history is per-session in the browser.
  Crossing devices means storing per-user history in Firestore.
- **Tool calling** — same gap as `chat.py`: agents can advise but not act on
  Cloud APIs. The per-agent BUILD.md files spell out the function-calling work
  required (e.g. Vin's Cloudflare/GitHub tools).
- **Custom domain** — `agents-web-<hash>-uc.a.run.app` works; map a real
  domain via `gcloud beta run domain-mappings create`.
- **Push notifications** — not in this PR. Service worker is set up; adding
  Web Push needs VAPID keys + a backend endpoint to send.
- **App icons** — not shipped (manifest currently has no `icons` array, browser
  uses default). Drop `icon-192.png` and `icon-512.png` into `app/static/` and
  re-add the `icons` entries to `manifest.webmanifest` for a proper home-screen
  icon on iOS/Android.

---

## Useful commands

```bash
gcloud run services logs tail agents-web --project=samantha-493919 --region=us-central1
gcloud run services describe agents-web --project=samantha-493919 --region=us-central1
```
