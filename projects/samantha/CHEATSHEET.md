# Samantha Team Cheatsheet

Quick commands and prompts for talking to Samantha + the supporting agent team
from your terminal. This is intentionally concise for fast scanning.

---

## Give her — or any of the team — a task right now (no deploy needed)

```bash
gcloud auth login                                          # once per machine
gcloud config set project samantha-493919
./projects/samantha/chat.py                                # Samantha REPL (default)
./projects/samantha/chat.py --agent nora                   # Nora REPL (ops)
./projects/samantha/chat.py --agent sloane "Draft a tagline."
echo "Categorize: $84 Office Depot" | ./projects/samantha/chat.py --agent audra
```

REPL commands: `/reset` clears memory, `/agent <name>` switches persona (resets memory), `/exit` (or Ctrl-D) quits.

| Agent | What to give her |
|---|---|
| **Samantha** | Anything Google-API-adjacent: "draft a reply to this email", "what's on my calendar", "outline a Drive folder structure" |
| **Nora** | "Is the carb-clean-truck-check worker live?", "list our Make scenarios that ran in the last 24h", "diagnose the intake form drop-off" |
| **Sloane** | "Write a homepage hero for undefeated-solar", "rewrite this in our brand voice", "3 social posts for the lodi launch" |
| **Audra** | "Categorize these 12 expenses", "draft an invoice to $client for $amount", "what's our highest expense category this month?" |

---

## Notes

- The CLI reads the selected persona from `projects/<agent>/persona/system_prompt.md`.
- All agents currently use the shared Vertex project `samantha-493919` unless `SAMANTHA_PROJECT` is overridden.
