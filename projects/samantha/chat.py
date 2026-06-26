#!/usr/bin/env python3
"""Samantha — talk-to-her CLI.

Sends a task directly to Vertex AI Gemini in samantha-493919 with the persona
system prompt loaded from persona/system_prompt.md. Works WITHOUT the Cloud
Run service being live, so you can give Samantha tasks tonight even if the
container deploy is still in flight.

Auth uses your gcloud login (gcloud auth print-access-token). If you're not
logged in, run: gcloud auth login && gcloud config set project samantha-493919

Usage:
  ./projects/samantha/chat.py "Plan my Tuesday"
  echo "Plan my Tuesday" | ./projects/samantha/chat.py
  SAMANTHA_MODEL=gemini-1.5-flash ./projects/samantha/chat.py "Quick draft please"

This is for personal / iterative use; production traffic goes through the
deployed Cloud Run service (see BUILD.md).
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

PROJECT = os.environ.get("SAMANTHA_PROJECT", "samantha-493919")
REGION = os.environ.get("SAMANTHA_REGION", "us-central1")
MODEL = os.environ.get("SAMANTHA_MODEL", "gemini-1.5-pro")
PERSONA_FILE = pathlib.Path(__file__).parent / "persona" / "system_prompt.md"


def extract_persona(path: pathlib.Path) -> str:
    content = path.read_text()
    start, end = "<!-- BEGIN SYSTEM PROMPT -->", "<!-- END SYSTEM PROMPT -->"
    s, e = content.find(start), content.find(end)
    if s == -1 or e == -1:
        sys.exit(f"BEGIN/END SYSTEM PROMPT markers missing in {path}")
    return content[s + len(start) : e].strip()


def access_token() -> str:
    try:
        return subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except FileNotFoundError:
        sys.exit("gcloud CLI not found on PATH — see SETUP.md")
    except subprocess.CalledProcessError:
        sys.exit("gcloud not authenticated. Run: gcloud auth login")


def task_from_args() -> str:
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    sys.exit(f"Usage: {sys.argv[0]} <task>   or   echo <task> | {sys.argv[0]}")


def main() -> None:
    persona = extract_persona(PERSONA_FILE)
    task = task_from_args()
    token = access_token()

    endpoint = (
        f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{REGION}/publishers/google/models/{MODEL}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": persona}]},
        "contents": [{"role": "user", "parts": [{"text": task}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from Vertex AI:\n{e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e}")

    try:
        print(body["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError):
        print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
