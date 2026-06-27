#!/usr/bin/env python3
"""Sync GitHub + Drive READMEs into projects/samantha/persona/knowledge/.

This populates the RAG drop zones the agents read at chat time so they're
grounded on actual project history — not just the persona prompt.

Three sources:
  1. GitHub org READMEs    -> persona/knowledge/synced-github/<repo>.md
  2. Google Drive READMEs  -> persona/knowledge/synced-drive/<title>-<id>.md
  3. This repo's CLAUDE.md -> persona/knowledge/synced-repo/CLAUDE.md

Auth:
  GITHUB_TOKEN env var   — classic or fine-grained PAT with `repo` (read) scope
                           on the BelichickGillisMusk org. Required for private
                           repos; public repos work without one (rate-limited).
  Google Drive           — uses ADC (`gcloud auth application-default login`)
                           with the Drive read scope. Requires the Drive API
                           enabled on the active GCP project.

Usage:
  GITHUB_ORG=BelichickGillisMusk GITHUB_TOKEN=ghp_... python3 scripts/sync_knowledge.py
  python3 scripts/sync_knowledge.py --skip-drive       # if you don't have Drive ADC
  python3 scripts/sync_knowledge.py --skip-github      # Drive only

Idempotent: re-runs overwrite existing files in the synced-* directories. Files
NOT in synced-* are left alone (those are hand-curated knowledge).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "projects" / "samantha" / "persona" / "knowledge"
GITHUB_DIR = KNOWLEDGE_DIR / "synced-github"
DRIVE_DIR = KNOWLEDGE_DIR / "synced-drive"
REPO_DIR = KNOWLEDGE_DIR / "synced-repo"


def _ghhttp(path: str, token: str | None) -> dict | list:
    url = f"https://api.github.com{path}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "samantha-sync/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_org_repos(org: str, token: str | None) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        batch = _ghhttp(
            f"/orgs/{urllib.parse.quote(org)}/repos?per_page=100&page={page}&type=all",
            token,
        )
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def fetch_readme(owner: str, repo: str, token: str | None) -> str | None:
    """Return README text, or None if no README on default branch."""
    try:
        data = _ghhttp(f"/repos/{owner}/{repo}/readme", token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    if not isinstance(data, dict) or "content" not in data:
        return None
    import base64
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


def slugify(s: str) -> str:
    return _SLUG_RE.sub("-", s).strip("-").lower() or "untitled"


def sync_github(org: str, token: str | None) -> int:
    GITHUB_DIR.mkdir(parents=True, exist_ok=True)
    repos = list_org_repos(org, token)
    print(f"[github] {len(repos)} repos in {org}", file=sys.stderr)
    written = 0
    for r in repos:
        if r.get("archived"):
            continue
        name = r["name"]
        # Skip Cloudflare auto-named throwaways and obvious test repos
        if re.fullmatch(r"[a-z]+-[a-z]+-\d+|1111", name.lower()):
            continue
        try:
            content = fetch_readme(org, name, token)
        except urllib.error.HTTPError as e:
            print(f"[github] {name}: HTTP {e.code} skip", file=sys.stderr)
            continue
        except Exception as e:
            print(f"[github] {name}: {e} skip", file=sys.stderr)
            continue
        if not content or len(content.strip()) < 40:
            continue
        out = GITHUB_DIR / f"{slugify(name)}.md"
        out.write_text(
            f"<!-- source: github.com/{org}/{name} -->\n"
            f"# {name}\n\n{content.strip()}\n",
            encoding="utf-8",
        )
        written += 1
    print(f"[github] wrote {written} README files to {GITHUB_DIR.relative_to(REPO_ROOT)}", file=sys.stderr)
    return written


def sync_drive() -> int:
    """Use ADC to list Drive markdown files titled README* and write content."""
    try:
        from google.auth.transport.requests import AuthorizedSession
        import google.auth
    except ImportError:
        print("[drive] google-auth not installed: pip install google-auth", file=sys.stderr)
        return 0
    DRIVE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
    except Exception as e:
        print(f"[drive] no ADC ({e}). Run: gcloud auth application-default login --scopes=...", file=sys.stderr)
        return 0
    sess = AuthorizedSession(creds)
    q = (
        "(title contains 'README' or title contains 'readme') "
        "and (mimeType = 'text/markdown' or mimeType = 'text/plain') "
        "and trashed = false"
    )
    written = 0
    page_token = None
    while True:
        params = {
            "q": q,
            "fields": "nextPageToken,files(id,name,parents,modifiedTime,size)",
            "pageSize": "1000",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        r = sess.get("https://www.googleapis.com/drive/v3/files", params=params, timeout=30)
        if r.status_code != 200:
            print(f"[drive] list HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
            break
        body = r.json()
        for f in body.get("files", []):
            fid = f["id"]
            name = f.get("name", "README.md")
            dl = sess.get(
                f"https://www.googleapis.com/drive/v3/files/{fid}",
                params={"alt": "media", "supportsAllDrives": "true"},
                timeout=30,
            )
            if dl.status_code != 200:
                continue
            text = dl.text
            if len(text.strip()) < 40:
                continue
            out = DRIVE_DIR / f"{slugify(name)}-{fid[:8]}.md"
            out.write_text(
                f"<!-- source: drive.google.com/file/d/{fid} -->\n"
                f"# {name}\n\n{text.strip()}\n",
                encoding="utf-8",
            )
            written += 1
        page_token = body.get("nextPageToken")
        if not page_token:
            break
    print(f"[drive] wrote {written} README files to {DRIVE_DIR.relative_to(REPO_ROOT)}", file=sys.stderr)
    return written


def sync_repo_self() -> int:
    """Copy this repo's CLAUDE.md into the knowledge dir so it's available like the rest."""
    REPO_DIR.mkdir(parents=True, exist_ok=True)
    src = REPO_ROOT / "CLAUDE.md"
    if not src.exists():
        return 0
    out = REPO_DIR / "CLAUDE.md"
    out.write_text(
        "<!-- source: this repo's CLAUDE.md -->\n" + src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    print(f"[repo] copied CLAUDE.md to {out.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--org", default=os.environ.get("GITHUB_ORG", "BelichickGillisMusk"))
    ap.add_argument("--skip-github", action="store_true")
    ap.add_argument("--skip-drive", action="store_true")
    ap.add_argument("--skip-self", action="store_true")
    args = ap.parse_args()

    total = 0
    if not args.skip_github:
        total += sync_github(args.org, os.environ.get("GITHUB_TOKEN"))
    if not args.skip_drive:
        total += sync_drive()
    if not args.skip_self:
        total += sync_repo_self()
    print(f"synced {total} files into {KNOWLEDGE_DIR.relative_to(REPO_ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
