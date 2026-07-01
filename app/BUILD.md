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

# Simpler one-shot using the committed app/cloudbuild.yaml (recommended):
gcloud builds submit . --project=samantha-493919 --region=us-central1 \
  --config=app/cloudbuild.yaml --substitutions=_IMAGE="$IMAGE"
```

`app/cloudbuild.yaml` ships in this folder and builds with `-f app/Dockerfile`
from the repo-root context, so no file moving is needed. To skip Cloud Build
entirely, build locally instead:

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

## Embed on bryanoneillgillis.com (the "Samantha box")

Once `agents-web` is deployed and you have its URL — say
`https://agents-web-xyz.us-central1.run.app` — embed it on the site as a
floating chat panel:

```html
<!-- paste in your site footer or template -->
<style>
  #agents-launcher {
    position: fixed; right: 20px; bottom: 20px; z-index: 9999;
    width: 56px; height: 56px; border-radius: 50%;
    background: #0b0d12; color: #fff; border: 0; cursor: pointer;
    box-shadow: 0 6px 20px rgba(0,0,0,.25); font-size: 24px;
  }
  #agents-panel {
    position: fixed; right: 20px; bottom: 90px; z-index: 9998;
    width: min(380px, 92vw); height: min(640px, 80vh);
    border: 1px solid #262a39; border-radius: 14px; overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,.35);
    display: none; background: #0b0d12;
  }
  #agents-panel iframe { width: 100%; height: 100%; border: 0; display: block; }
  #agents-panel.open { display: block; }
</style>
<button id="agents-launcher" aria-label="Open agents">💬</button>
<div id="agents-panel" role="dialog" aria-label="Bryan's agents">
  <iframe src="https://agents-web-xyz.us-central1.run.app/"
          allow="microphone"></iframe>
</div>
<script>
  document.getElementById('agents-launcher').addEventListener('click', () =>
    document.getElementById('agents-panel').classList.toggle('open'));
</script>
```

Three things to know:

- **`allow="microphone"`** is required for the 🎙 voice-**input** (dictation)
  button to work inside the iframe. Without it the mic prompt is silently denied.
  Voice **output** (the 🔊 read-aloud button on replies) uses the browser's
  `speechSynthesis` and needs no permission or iframe attribute. Each agent speaks
  in a gender-matched voice — women's voices for Samantha/Nora/Sloane/Audra, a
  man's voice for Vin — falling back to a pitch offset when the browser exposes no
  distinctly-gendered voice.
- **CORS is off by default.** The iframe approach above works because the
  PWA's `fetch('/api/chat')` calls are same-origin (the iframe loaded from
  `agents-web-xyz.run.app`, the fetch goes to the same host). If you instead
  drop the iframe and call `/api/chat` directly from bryanoneillgillis.com JS,
  set the deploy-time env var
  `CORS_ALLOW_ORIGINS=https://bryanoneillgillis.com` so the backend whitelists
  that origin (intentionally not `*` — open CORS on an unauthenticated model
  proxy invites cost abuse from any random site).
- **Cloud Run does not set `X-Frame-Options`** so the iframe loads fine from
  any origin in v1. If you later add Cloud IAP or a CDN that *does* set
  `X-Frame-Options: DENY`, you'll need a `frame-ancestors` CSP override.

For Squarespace / Webflow / Wix: paste the snippet into the site's "code
injection" or "custom HTML" footer slot.

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

## Knowledge grounding (GitHub READMEs + Drive + CLAUDE.md)

Each agent's chat call now prepends every `.md` file under
`projects/<agent>/persona/knowledge/` to the system prompt as a "reference
documents" block — same wiring `chat.py` uses, so the web app and CLI stay
in sync.

Populate the knowledge dir with `scripts/sync_knowledge.py`. By default it
only pulls READMEs from repos / Drive files touched **since 2026-04-01** —
the cutoff where the norcalcarbmobile stack and overall team tech-capability
shifted. Older docs would just confuse the agents about the current state of
the world.

```bash
# GitHub org READMEs (requires a PAT with repo:read on BelichickGillisMusk):
GITHUB_TOKEN=ghp_... python3 scripts/sync_knowledge.py --skip-drive

# Google Drive READMEs (uses gcloud ADC with Drive read scope):
gcloud auth application-default login --scopes=\
'https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/cloud-platform'
python3 scripts/sync_knowledge.py --skip-github

# Both, and re-copy this repo's CLAUDE.md into the knowledge dir:
GITHUB_TOKEN=ghp_... python3 scripts/sync_knowledge.py

# Override the date cutoff:
python3 scripts/sync_knowledge.py --since 2026-01-01    # broader history
python3 scripts/sync_knowledge.py --since 2026-06-01    # last month only
```

The script writes to three subdirs (idempotent — re-running overwrites):

- `projects/samantha/persona/knowledge/synced-github/<repo>.md`
- `projects/samantha/persona/knowledge/synced-drive/<title>-<id>.md`
- `projects/samantha/persona/knowledge/synced-repo/CLAUDE.md`

Hand-curated files in `persona/knowledge/` (anywhere else) are left alone.
Disable knowledge entirely by setting `SAMANTHA_NO_KNOWLEDGE=1` on the
container, or cap the prepended bytes with `SAMANTHA_MAX_KNOWLEDGE_BYTES`
(default `800000` = ~200K tokens, well under Gemini 2.5 Pro's window).

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
