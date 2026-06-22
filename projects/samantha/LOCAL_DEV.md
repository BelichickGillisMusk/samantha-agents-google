# Samantha — Local Development Harness (Ollama + Open WebUI)

> **This is a local development / offline-prototyping environment, not a
> production deployment.** Production Samantha runs on **Cloud Run + Vertex AI /
> Gemini** — see [BUILD.md](BUILD.md). Use this stack to iterate on Samantha's
> **persona** and **RAG knowledge** quickly, offline, and without spending
> Vertex tokens or needing GCP auth.

---

## How this fits with the GCP setup

The two environments deliberately share **two artifacts** so the local and cloud
Samantha don't drift apart:

| Shared artifact | Production (GCP) | Local (this stack) |
|---|---|---|
| [`persona/system_prompt.md`](persona/system_prompt.md) | Loaded as the system prompt for Gemini | Pasted into the Open WebUI Modelfile system prompt |
| [`persona/knowledge/`](persona/knowledge/) | Indexed into Vertex AI Search / vector store | Uploaded into Open WebUI **Documents** for RAG |

Edit the persona and knowledge **once**, in those shared files, and apply them to
both backends. Everything else differs by design:

| | Production | Local |
|---|---|---|
| **Model** | Gemini (`gemini-1.5-pro`) via Vertex AI | Open-weight model via Ollama (Llama 3 / Mistral) |
| **Runtime** | Cloud Run (managed, autoscaling) | Docker on your machine |
| **Cost** | Per-token + Cloud Run | Free (your hardware) |

> ⚠️ **The local model is not Gemini.** Ollama serves open-weight models only, so
> answers will differ from production. This stack is for persona/UX/RAG iteration,
> **not** for validating production behavior. (If you ever need the *exact*
> production model behind this UI, point Open WebUI at Vertex via an
> OpenAI-compatible proxy such as LiteLLM — see [Appendix](#appendix-unified-front-end-optional)
> — but that reintroduces GCP auth and token cost.)

> ⚠️ **`ollama run samantha` pulls an unrelated community model** that merely
> shares the name. *This* Samantha is defined by the shared persona file above
> layered on a capable base model. Start from a strong base (e.g. `llama3`) and
> apply our system prompt — do **not** rely on the `samantha` tag as our agent.

---

## Prerequisites

- Docker 24+ (see [SETUP.md](../../SETUP.md))
- The repo's `.env` file with a `WEBUI_SECRET_KEY` set (below)

---

## 1. Set the secret

The compose file reads `WEBUI_SECRET_KEY` from the repo's `.env` — it is **never**
hardcoded, consistent with this repo's "never commit secrets" rule.

```bash
cp ../../.env.example ../../.env          # if you don't have a .env yet
# Generate a key and add it to .env:
echo "WEBUI_SECRET_KEY=$(openssl rand -hex 32)" >> ../../.env
```

## 2. Start the stack

```bash
# from projects/samantha/
docker compose --env-file ../../.env up -d
```

Open WebUI is then available at <http://localhost:3000>. Local models, chats, and
uploaded documents persist in `./ollama` and `./open-webui` (both git-ignored).

## 3. Pull a base model

```bash
docker exec -it ollama ollama run llama3
```

## 4. Create the "Samantha" model in Open WebUI

1. Open <http://localhost:3000> → **Workspace → Models → Create a model**.
2. Base model: the one you pulled (e.g. `llama3`).
3. **System prompt:** paste the prompt from
   [`persona/system_prompt.md`](persona/system_prompt.md) (the text between the
   `BEGIN`/`END SYSTEM PROMPT` markers).
4. Save as `samantha-local`.

## 5. Load the knowledge base (RAG)

1. **Documents** → upload the files from
   [`persona/knowledge/`](persona/knowledge/).
2. In chat with `samantha-local`, tag the documents (`#`) so Samantha grounds her
   answers on them.

## 6. Stop / reset

```bash
docker compose down            # stop (keeps volumes / data)
docker compose down -v && rm -rf ollama open-webui   # full reset
```

---

## Appendix: a friendly hostname (optional)

To "log into the office" at a memorable address instead of `localhost:3000`, map a
hostname to your loopback address in your hosts file:

```bash
# Linux/macOS: /etc/hosts   (Windows: C:\Windows\System32\drivers\etc\hosts)
echo "127.0.0.1  office.local" | sudo tee -a /etc/hosts
```

Then browse to <http://office.local:3000>. This is a purely local convenience and
has no effect on the GCP deployment. To serve it on the bare `office.local`
(no `:3000`), front Open WebUI with a reverse proxy listening on port 80.

---

## Appendix: unified front-end (optional)

If you specifically want the **production Gemini model** behind this same Open
WebUI, run a [LiteLLM](https://github.com/BerriAI/litellm) proxy exposing Vertex
as an OpenAI-compatible endpoint and add it under **Settings → Connections** in
Open WebUI. This gives one UI for both local and cloud backends, but it needs GCP
auth (`gcloud auth application-default login`) and incurs Vertex token cost — so
it is not the default for local iteration.
