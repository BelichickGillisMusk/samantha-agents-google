#!/usr/bin/env python3
"""Agent — talk-to-her CLI for Samantha, Nora, Sloane, Audra, and Vin.

Sends tasks directly to Vertex AI Gemini with the chosen agent's persona system
prompt loaded from projects/<agent>/persona/system_prompt.md. Works WITHOUT
the per-agent Cloud Run service being live, so each agent is reachable today
regardless of deploy state.

Usage:

  ./projects/samantha/chat.py                          # Samantha REPL (default)
  ./projects/samantha/chat.py --agent nora             # Nora REPL (ops monitoring)
  ./projects/samantha/chat.py --agent sloane "Draft a tagline for the rebrand."
  echo "Categorize this expense: $84 Office Depot." | ./projects/samantha/chat.py --agent audra
  ./projects/samantha/chat.py --agent vin "Plan a clean-up sweep of the 7 stub Workers."

REPL commands: /reset clears memory · /exit (or Ctrl-D) quits · /agent <name>
switches persona mid-session (memory is wiped — different agent, different
context).

Auth uses your gcloud login (gcloud auth print-access-token). All five agents
currently call Vertex AI in samantha-493919 (one project, five personas) —
override with SAMANTHA_PROJECT if you split them later.
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

AGENTS = ("samantha", "nora", "sloane", "audra", "vin")

PROJECT = os.environ.get("SAMANTHA_PROJECT", "samantha-493919")
REGION = os.environ.get("SAMANTHA_REGION", "us-central1")
MODEL = os.environ.get("SAMANTHA_MODEL", "gemini-1.5-pro")
PROJECTS_DIR = pathlib.Path(__file__).resolve().parent.parent


def persona_path(agent: str) -> pathlib.Path:
    if agent not in AGENTS:
        sys.exit(f"Unknown agent '{agent}'. Choose from: {', '.join(AGENTS)}")
    return PROJECTS_DIR / agent / "persona" / "system_prompt.md"


def extract_persona(path: pathlib.Path) -> str:
    if not path.exists():
        sys.exit(f"Persona file not found: {path}")
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


def repl(agent: str, token: str) -> None:
    persona = extract_persona(persona_path(agent))
    name = agent.capitalize()
    print(
        f"{name} is on — model={MODEL}, project={PROJECT}.\n"
        f"Type a task and press Enter. /reset clears memory, /agent <name> "
        f"switches persona, /exit (or Ctrl-D) quits.\n"
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
        if line.startswith("/agent "):
            new_agent = line.split(maxsplit=1)[1].strip().lower()
            if new_agent not in AGENTS:
                print(f"Unknown agent. Choose: {', '.join(AGENTS)}\n")
                continue
            agent = new_agent
            persona = extract_persona(persona_path(agent))
            name = agent.capitalize()
            contents.clear()
            print(f"(switched to {name}, conversation reset)\n")
            continue
        contents.append({"role": "user", "parts": [{"text": line}]})
        reply = call_gemini(persona, contents, token)
        contents.append({"role": "model", "parts": [{"text": reply}]})
        print(f"\n{name}: {reply}\n")


def parse_argv(argv: list) -> tuple:
    """Return (agent, remaining_args). Pops '--agent <name>' if present."""
    agent = "samantha"
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] == "--agent" and i + 1 < len(argv):
            agent = argv[i + 1].lower()
            i += 2
        elif argv[i].startswith("--agent="):
            agent = argv[i].split("=", 1)[1].lower()
            i += 1
        else:
            rest.append(argv[i])
            i += 1
    return agent, rest


def main() -> None:
    agent, rest = parse_argv(sys.argv[1:])
    token = access_token()

    if rest:
        persona = extract_persona(persona_path(agent))
        task = " ".join(rest)
        print(call_gemini(persona, [{"role": "user", "parts": [{"text": task}]}], token))
        return
    if not sys.stdin.isatty():
        persona = extract_persona(persona_path(agent))
        task = sys.stdin.read().strip()
        if not task:
            sys.exit("Empty task on stdin.")
        print(call_gemini(persona, [{"role": "user", "parts": [{"text": task}]}], token))
        return
    repl(agent, token)


if __name__ == "__main__":
    main()
