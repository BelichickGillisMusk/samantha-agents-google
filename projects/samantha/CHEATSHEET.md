# Samantha — Cheatsheet

A one-page "what's the thing?" reference for when you've forgotten. Optimized
for fast scanning, not exhaustive — full detail in [`BUILD.md`](BUILD.md) and
[`LOCAL_DEV.md`](LOCAL_DEV.md).

---

## What she is (in 5 lines)

- **Model:** Vertex AI **Gemini 1.5 Pro**, hosted in GCP project `samantha-493919` (us-central1).
- **Persona:** [`persona/system_prompt.md`](persona/system_prompt.md), between the `BEGIN`/`END SYSTEM PROMPT` markers. One file feeds both production and local dev.
- **Production hosting:** Cloud Run service named `samantha`, deployed from a container image in Artifact Registry.
- **Local talk-to-her CLI:** [`chat.py`](chat.py) — Vertex AI direct, no Cloud Run required.
- **Credential:** the broad Google API key lives in GCP Secret Manager as `Samantha_App_Key` (mixed case), mirrored from the BelichickGillisMusk org-level GitHub Actions secret `SAMANTHA_APP_KEY` (all-caps).

---

## Give her — or any of the team — a task right now (no deploy needed)

```bash
gcloud auth login                                          # once per machine
gcloud config set project samantha-493919
./projects/samantha/chat.py                                # Samantha REPL (default)
./projects/samantha/chat.py --agent nora                   # Nora REPL (ops monitoring)
./projects/samantha/chat.py --agent sloane "Draft a tagline."
echo "Categorize: $84 Office Depot" | ./projects/samantha/chat.py --agent audra
./projects/samantha/chat.py --agent vin "Plan a cleanup of the 7 stub Workers."
```

REPL commands: `/reset` clears memory, `/agent <name>` switches persona (resets memory), `/exit` (or Ctrl-D) quits.

| Agent | What to give her / him |
|---|---|
| **Samantha** | Google-API-adjacent: "draft a reply to this email", "what's on my calendar", "outline a Drive folder structure" |
| **Nora** | "Is the carb-clean-truck-check worker live?", "list Make scenarios that ran in the last 24h", "diagnose the intake form drop-off" |
| **Sloane** | "Write a homepage hero for undefeated-solar", "rewrite this in our brand voice", "3 social posts for the lodi launch" |
| **Audra** | "Categorize these 12 expenses", "draft an invoice to $client for $amount", "what's our highest expense category this month?" |
| **Vin** | "Plan the cleanup sweep of the 7 stub Workers", "draft a PR description for the X change", "what's the safest rollback path for the carb-clean-truck-check deploy?" |

---

## Production deploy (Cloud Run)

```bash
# 1. Build image
IMAGE="us-central1-docker.pkg.dev/samantha-493919/agents/samantha:$(git rev-parse --short HEAD)"
gcloud builds submit --project=samantha-493919 --region=us-central1 --tag="$IMAGE"

# 2. Deploy with env vars + secret bound (DON'T skip --set-secrets)
gcloud run deploy samantha --project=samantha-493919 --region=us-central1 \
  --image="$IMAGE" --platform=managed --allow-unauthenticated --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=samantha-493919,VERTEX_AI_MODEL=gemini-1.5-pro" \
  --set-secrets="SAMANTHA_APP_KEY=Samantha_App_Key:latest"

# 3. Verify
./projects/samantha/smoke_test.sh "Hello"
```

---

## "Wait, what was that name…?" — the casing trap

Same value, three different cases. **Don't try to "normalize" them.**

| Where it lives | Name | Notes |
|---|---|---|
| GitHub org secret (public-repo scope) | `SAMANTHA_APP_KEY` | all caps |
| GitHub org secret (private-repo scope) | `SAMANTHA` | unverified if same value |
| GCP Secret Manager (`samantha-493919`) | `Samantha_App_Key` | mixed case — case-sensitive |
| Container env var | `SAMANTHA_APP_KEY` | all caps (Linux convention) |

---

## Useful one-liners

```bash
# Tail production logs
gcloud run services logs tail samantha --project=samantha-493919 --region=us-central1

# What URL is live, what env/secrets are bound?
gcloud run services describe samantha --project=samantha-493919 --region=us-central1

# Roll back to a previous revision
gcloud run revisions list --service=samantha --project=samantha-493919 --region=us-central1
gcloud run services update-traffic samantha --project=samantha-493919 --region=us-central1 \
  --to-revisions=<revision-name>=100

# Rotate the API key (after updating GitHub side separately)
printf '%s' "$NEW_VALUE" | gcloud secrets versions add Samantha_App_Key \
  --project=samantha-493919 --data-file=-

# Enable an API she needs (e.g. Gmail, Calendar)
gcloud services enable gmail.googleapis.com --project=samantha-493919
```

---

## What you can ask her today

Out of the box (just `chat.py` or the deployed Cloud Run service, no extra wiring):

- Drafting / rewriting — emails, posts, replies, descriptions, summaries.
- Planning — daily / weekly schedules, project breakdowns, agenda outlines.
- Decision support — pros/cons, tradeoffs, "which option is better for X".
- Brand-voice copy for bryanoneillgillis.com — she's prompted as the COA.
- Brainstorming — campaign ideas, naming, positioning.
- Q&A grounded on whatever you paste in — she'll say "outside my docs" if she doesn't know.

She is currently **chat-only**. She can describe what an email should say, but
she cannot send it herself — sending requires a tool/function-calling layer
that doesn't exist in this repo yet (see the next section).

---

## Surfaces she could live in (roadmap, not built yet)

| Surface | Built? | How |
|---|---|---|
| Local CLI (`chat.py`) | ✅ | Already in this repo. |
| Cloud Run HTTP service | ⚠️ partial | Service is deploy-able; you'll need a frontend (web page, Slack bot, etc.) calling its chat endpoint. |
| Open WebUI (local web app) | ✅ | `docker compose up` from `projects/samantha/`, see [`LOCAL_DEV.md`](LOCAL_DEV.md). Uses an open-weight model, not Gemini, but same persona. |
| Web app frontend | ❌ | Build any static site (React / plain HTML / Webflow) that POSTs to the Cloud Run URL's chat endpoint. |
| Google Chat bot | ❌ | Register a Google Chat app in `samantha-493919` (Chat API → "Configuration"), point it at a Cloud Run / Cloud Function webhook that forwards messages to `chat.py`-style code. |
| Gmail "send email" | ❌ | Enable `gmail.googleapis.com` on `samantha-493919`, grant the runtime SA the right OAuth scope (domain-wide delegation for org Gmail or per-user OAuth), wire a tool call. |
| Calendar / Drive | ❌ | Same pattern as Gmail — enable the API on `samantha-493919`, grant the SA the scope, wire a tool call. |
| Slack | ❌ | Slack app + webhook + Cloud Run handler that forwards to her. |

For each "❌", the work is roughly: enable the Google API → grant the runtime
service account the right scope (or set up OAuth on the user's behalf) → add a
tool definition in her container code so Gemini can call it via function
calling. None of that lives in this docs repo today.

---

## Files you'll touch most

```
projects/samantha/
├── BUILD.md             ← deploy + ops detail
├── CHEATSHEET.md        ← this file
├── LOCAL_DEV.md         ← Open WebUI local stack
├── chat.py              ← talk-to-her CLI (uses Vertex AI directly)
├── smoke_test.sh        ← post-deploy verifier
├── docker-compose.yml   ← local Ollama + Open WebUI
└── persona/
    ├── system_prompt.md ← edit her personality + tone here
    └── knowledge/       ← RAG reference docs
```

---

## When things go wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `chat.py` says `gcloud not authenticated` | gcloud login expired | `gcloud auth login` |
| `HTTP 403 aiplatform.googleapis.com has not been used` | API disabled on project | `gcloud services enable aiplatform.googleapis.com --project=samantha-493919` |
| Cloud Run deploy: `secret SAMANTHA_APP_KEY not found` | case mismatch — secret name is `Samantha_App_Key`, not `SAMANTHA_APP_KEY` | use `--set-secrets="SAMANTHA_APP_KEY=Samantha_App_Key:latest"` |
| Cloud Run: container responds 500 | check live logs | `gcloud run services logs tail samantha --project=samantha-493919 --region=us-central1` |
| `chat.py` reply doesn't sound like Samantha | persona file edited but markers removed | check `persona/system_prompt.md` still has `<!-- BEGIN/END SYSTEM PROMPT -->` markers |
| You can't remember the project ID | look here | `samantha-493919` |
