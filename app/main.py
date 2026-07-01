"""bryanoneillgillis agents — web backend.

One Cloud Run service that fronts all five agents (Samantha, Nora, Sloane,
Audra, Vin). Each chat call:
  1. resolves the agent's persona file from projects/<agent>/persona/system_prompt.md
  2. authenticates to Gemini:
       - SAMANTHA_APP_KEY set → Gemini AI Studio API (generativelanguage.googleapis.com)
         using the API key directly; no ADC / service account needed.
       - SAMANTHA_APP_KEY absent → Vertex AI (aiplatform.googleapis.com) via ADC;
         in Cloud Run the runtime service account supplies the credential automatically.
  3. POSTs to gemini-2.5-pro:generateContent
  4. returns the model's reply

Static frontend (single-page PWA) lives in app/static/ and is served from /.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import List

import google.auth
import google.auth.transport.requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "projects" / "samantha"))
import chat  # noqa: E402 — reuses extract_persona, persona_path, AGENTS

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "samantha-493919")
# Prefer VERTEX_AI_REGION (the repo's documented env name) so Cloud Run region
# and Vertex region can differ; fall back to GOOGLE_CLOUD_REGION then default.
REGION = (
    os.environ.get("VERTEX_AI_REGION")
    or os.environ.get("GOOGLE_CLOUD_REGION")
    or "us-central1"
)
MODEL = os.environ.get("VERTEX_AI_MODEL", "gemini-2.5-pro")
# When set, use the Gemini AI Studio API with key-based auth instead of Vertex AI + ADC.
# In Cloud Run this is mounted from Secret Manager via --set-secrets; locally, set it in .env.
APP_KEY = os.environ.get("SAMANTHA_APP_KEY", "")
STATIC_DIR = pathlib.Path(__file__).parent / "static"

# CORS allowlist for cross-origin embeds (e.g. bryanoneillgillis.com). Comma-
# separated; default empty -> CORS middleware NOT installed, so any third-party
# site cannot use this unauthenticated service as a free model proxy.
CORS_ALLOW_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()
]

app = FastAPI(title="bryanoneillgillis agents", version="1.0")
# Same-origin (the PWA frontend served from /) doesn't need CORS. Only enable
# the middleware if the operator explicitly lists allowed origins — avoids
# the abuse risk of an open unauthenticated model proxy.
if CORS_ALLOW_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type", "Authorization"],
    )


VALID_ROLES = {"user", "model"}


class Turn(BaseModel):
    role: str  # must be "user" or "model" — validated in chat_endpoint
    text: str


class ChatRequest(BaseModel):
    agent: str
    message: str
    history: List[Turn] = []


def _gemini_url() -> str:
    """Endpoint URL. API-key path uses AI Studio; ADC path uses Vertex AI."""
    if APP_KEY:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    return (
        f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{REGION}/publishers/google/models/{MODEL}:generateContent"
    )


def _gemini_headers() -> dict:
    """Auth headers. API key takes precedence over ADC."""
    if APP_KEY:
        return {"x-goog-api-key": APP_KEY, "Content-Type": "application/json"}
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return {"Authorization": "Bearer " + creds.token, "Content-Type": "application/json"}


@app.get("/api/agents")
def list_agents() -> dict:
    return {"agents": list(chat.AGENTS), "model": MODEL, "project": PROJECT}


@app.get("/api/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest) -> dict:
    if req.agent not in chat.AGENTS:
        raise HTTPException(400, f"Unknown agent: {req.agent}")
    if not req.message.strip():
        raise HTTPException(400, "Empty message")

    persona = chat.system_instruction(req.agent)
    contents = []
    for i, t in enumerate(req.history):
        if t.role not in VALID_ROLES:
            raise HTTPException(
                400, f"history[{i}].role must be one of {sorted(VALID_ROLES)}; got {t.role!r}"
            )
        contents.append({"role": t.role, "parts": [{"text": t.text}]})
    contents.append({"role": "user", "parts": [{"text": req.message}]})

    payload = {
        "systemInstruction": {"parts": [{"text": persona}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }
    url = _gemini_url()
    http_req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_gemini_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_req, timeout=60) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        raise HTTPException(e.code, e.read().decode(errors="replace"))
    except urllib.error.URLError as e:
        raise HTTPException(502, f"Network error: {e}")

    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        text = json.dumps(body)
    return {"agent": req.agent, "reply": text}


# Static frontend (PWA). Mount after API routes so /api/* wins.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return FileResponse(STATIC_DIR / "manifest.webmanifest")


@app.get("/sw.js")
def service_worker() -> FileResponse:
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")
