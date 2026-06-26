#!/usr/bin/env python3
"""Samantha — talk-to-her CLI.

Sends tasks directly to Vertex AI Gemini in samantha-493919 with the persona
system prompt loaded from persona/system_prompt.md. Works WITHOUT the Cloud
Run service being live, so you can give Samantha tasks tonight even if the
container deploy is still in flight.

Three modes:

  Interactive REPL (multi-turn, conversation memory):
    ./projects/samantha/chat.py
    > Plan my Tuesday — three priorities, 30 min each.
    Samantha: ...
    > Now reshuffle for Wednesday with a 9am dentist appointment.
    Samantha: ...
    > /exit         (or Ctrl-D)

  One-shot from argv (no memory):
    ./projects/samantha/chat.py "Plan my Tuesday"

  One-shot from stdin:
    echo "Plan my Tuesday" | ./projects/samantha/chat.py

Inside the REPL:
  /reset   — clear conversation history (keep persona)
  /exit    — quit (or Ctrl-D)

Auth uses your gcloud login (gcloud auth print-access-token). If you're not
logged in, run: gcloud auth login && gcloud config set project samantha-493919

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


def endpoint_url() -> str:
    return (
        f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{REGION}/publishers/google/models/{MODEL}:generateContent"
    )


def call_gemini(persona: str, contents: list, token: str) -> str:
    """POST to Vertex AI generateContent and return Samantha's text reply.

    `contents` is the running conversation list (user/model turns). The function
    raises on transport/HTTP errors and SystemExits on auth or empty replies.
    """
    payload = {
        "systemInstruction": {"parts": [{"text": persona}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }
    req = urllib.request.Request(
        endpoint_url(),
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
        return body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return json.dumps(body, indent=2)


def repl(persona: str, token: str) -> None:
    print(
        f"Samantha is on — model={MODEL}, project={PROJECT}.\n"
        "Type a task and press Enter. /reset clears memory. /exit (or Ctrl-D) quits.\n"
    )
    contents: list = []
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            return
        if not line:
            continue
        if line in ("/exit", "/quit"):
            return
        if line == "/reset":
            contents.clear()
            print("(conversation reset)\n")
            continue
        contents.append({"role": "user", "parts": [{"text": line}]})
        reply = call_gemini(persona, contents, token)
        contents.append({"role": "model", "parts": [{"text": reply}]})
        print(f"\nSamantha: {reply}\n")


def main() -> None:
    persona = extract_persona(PERSONA_FILE)
    token = access_token()

    # Mode selection
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        print(call_gemini(persona, [{"role": "user", "parts": [{"text": task}]}], token))
        return
    if not sys.stdin.isatty():
        task = sys.stdin.read().strip()
        if not task:
            sys.exit("Empty task on stdin.")
        print(call_gemini(persona, [{"role": "user", "parts": [{"text": task}]}], token))
        return
    repl(persona, token)


if __name__ == "__main__":
    main()
