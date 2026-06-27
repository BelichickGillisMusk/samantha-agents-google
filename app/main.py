"""bryanoneillgillis agents — web backend.

One Cloud Run service that fronts all five agents (Samantha, Nora, Sloane,
Audra, Vin). Each chat call:
  1. resolves the agent's persona file from projects/<agent>/persona/system_prompt.md
  2. authenticates to Vertex AI via the Cloud Run runtime service account (ADC)
  3. POSTs to gemini-2.5-pro:generateContent in samantha-493919/us-central1
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
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
MODEL = os.environ.get("VERTEX_AI_MODEL", "gemini-2.5-pro")
STATIC_DIR = pathlib.Path(__file__).parent / "static"

app = FastAPI(title="bryanoneillgillis agents", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Turn(BaseModel):
    role: str  # "user" or "model"
    text: str


class ChatRequest(BaseModel):
    agent: str
    message: str
    history: List[Turn] = []


def _access_token() -> str:
    """ADC token. In Cloud Run, the runtime service account supplies it."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


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

    persona = chat.extract_persona(chat.persona_path(req.agent))
    contents = [
        {"role": t.role, "parts": [{"text": t.text}]} for t in req.history
    ]
    contents.append({"role": "user", "parts": [{"text": req.message}]})

    payload = {
        "systemInstruction": {"parts": [{"text": persona}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }
    url = (
        f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{REGION}/publishers/google/models/{MODEL}:generateContent"
    )
    http_req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json",
        },
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
