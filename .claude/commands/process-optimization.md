---
description: Scaffold, configure, and deploy a new agent into this repo using the repo's conventions.
argument-hint: <agent-name> [one-line purpose]
---

Use the **process-optimization** agent (`.claude/agents/process-optimization.md`) to
stand up a new agent in this repository, following the same conventions as the
existing Samantha / Nora / Sloane agents.

Target agent (from the command arguments): `$ARGUMENTS`

Steps:

1. Read the existing agents under `projects/` and the README roster to mirror the
   established pattern exactly.
2. Scaffold `projects/<name>/BUILD.md`, `persona/system_prompt.md`, and
   `persona/knowledge/README.md`, substituting the agent name, the shared GCP
   project (`samantha-493919` — do not invent a `<name>-agent` project, which would
   cause GCP "Consumer invalid"), Cloud Run service (`<name>`), and persona.
3. Wire the new agent into `README.md` (roster table + repository-structure block).
4. Validate locally: grep for leftover template tokens; validate any added YAML.
5. Only touch GCP (Cloud Build / `gcloud run deploy`) if the user explicitly
   authorizes it; otherwise stop at scaffolding.
6. Commit on the working branch, push, and open a **draft** PR. Do not enable
   auto-merge.

If `<name>` or its purpose is missing and cannot be reasonably inferred, ask once,
then proceed.
