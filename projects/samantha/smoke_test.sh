#!/usr/bin/env bash
# Samantha — deploy smoke test
#
# Verifies the Samantha Cloud Run service is reachable, has the required env
# var + secret bindings, and can receive a task (HTTP POST). Run this after
# `gcloud run deploy samantha` to confirm "give her a task" works.
#
# Usage:
#   ./projects/samantha/smoke_test.sh                       # default: probe service root
#   ./projects/samantha/smoke_test.sh "Plan my Tuesday"     # send a real task to /chat
#   CHAT_PATH=/api/chat ./projects/samantha/smoke_test.sh "Hello"
#
# Exit codes:
#   0  everything reachable + 2xx/3xx response
#   1  gcloud CLI missing or unauthenticated
#   2  Cloud Run service not found or no URL
#   3  required env var / secret binding missing
#   4  HTTP request failed or non-2xx response

set -euo pipefail

PROJECT="${PROJECT:-samantha-493919}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-samantha}"
CHAT_PATH="${CHAT_PATH:-/chat}"
TASK="${1:-}"

red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

command -v gcloud  >/dev/null 2>&1 || { red "gcloud not on PATH";  exit 1; }
command -v curl    >/dev/null 2>&1 || { red "curl not on PATH";    exit 1; }
command -v python3 >/dev/null 2>&1 || { red "python3 not on PATH (used for safe JSON escaping)"; exit 1; }

ROOT_OUT="$(mktemp -t samantha_smoke_root.XXXXXX)"
CHAT_OUT="$(mktemp -t samantha_smoke_chat.XXXXXX)"
trap 'rm -f "$ROOT_OUT" "$CHAT_OUT"' EXIT

bold "── 1. Looking up Cloud Run service ──"
URL="$(gcloud run services describe "$SERVICE" \
  --project="$PROJECT" --region="$REGION" \
  --format='value(status.url)' 2>/dev/null || true)"

if [[ -z "$URL" ]]; then
  red "Service $SERVICE not found in $PROJECT / $REGION (or you're not authenticated)."
  red "Run: gcloud auth login && gcloud config set project $PROJECT"
  exit 2
fi
green "  URL: $URL"

bold "── 2. Checking env var + secret bindings ──"
DESCRIBE_JSON="$(gcloud run services describe "$SERVICE" \
  --project="$PROJECT" --region="$REGION" --format=json)"

REQUIRED_ENV=("GOOGLE_CLOUD_PROJECT" "VERTEX_AI_MODEL")
REQUIRED_SECRET_ENV="SAMANTHA_APP_KEY"

MISSING=()
for var in "${REQUIRED_ENV[@]}"; do
  if ! echo "$DESCRIBE_JSON" | grep -q "\"name\": \"$var\""; then
    MISSING+=("env:$var")
  fi
done
if ! echo "$DESCRIBE_JSON" | grep -q "\"name\": \"$REQUIRED_SECRET_ENV\""; then
  MISSING+=("secret-env:$REQUIRED_SECRET_ENV")
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
  red "  Missing bindings: ${MISSING[*]}"
  red "  Fix:"
  red "    gcloud run services update $SERVICE \\"
  red "      --project=$PROJECT --region=$REGION \\"
  red "      --set-env-vars=\"GOOGLE_CLOUD_PROJECT=$PROJECT,VERTEX_AI_MODEL=gemini-1.5-pro\" \\"
  red "      --set-secrets=\"SAMANTHA_APP_KEY=Samantha_App_Key:latest\""
  exit 3
fi
green "  All required env + secret bindings present."

bold "── 3. Probing service root (GET $URL/) ──"
HTTP_CODE="$(curl -sS -o "$ROOT_OUT" -w '%{http_code}' "$URL/" || true)"
echo "  HTTP $HTTP_CODE"
head -c 400 "$ROOT_OUT"; echo
case "$HTTP_CODE" in
  2*|3*) green "  Service root is reachable." ;;
  4*|5*) red "  Service root returned $HTTP_CODE — check Cloud Run logs:"
         red "    gcloud run services logs tail $SERVICE --project=$PROJECT --region=$REGION"
         exit 4 ;;
  *)     red "  No HTTP response (network / cold-start issue)"; exit 4 ;;
esac

if [[ -z "$TASK" ]]; then
  bold "── 4. Skipping task POST (no task supplied) ──"
  echo "  To send a real task: ./projects/samantha/smoke_test.sh \"Plan my Tuesday\""
  echo "  Override chat path with CHAT_PATH env var if your container uses something other than $CHAT_PATH."
  green ""
  green "Smoke test passed (deployment is live; task endpoint not exercised)."
  exit 0
fi

bold "── 4. Sending task to $URL$CHAT_PATH ──"
TOKEN="$(gcloud auth print-identity-token 2>/dev/null || true)"
AUTH_HEADER=()
[[ -n "$TOKEN" ]] && AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")

HTTP_CODE="$(curl -sS -o "$CHAT_OUT" -w '%{http_code}' \
  -X POST \
  -H 'Content-Type: application/json' \
  "${AUTH_HEADER[@]}" \
  --data "$(printf '{"message":%s}' "$(printf '%s' "$TASK" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")" \
  "$URL$CHAT_PATH" || true)"
echo "  HTTP $HTTP_CODE"
head -c 1500 "$CHAT_OUT"; echo
case "$HTTP_CODE" in
  2*) green ""; green "Samantha accepted the task. Goal: she's reachable for tasks."; exit 0 ;;
  4*|5*) red "  Task POST returned $HTTP_CODE — likely wrong CHAT_PATH or auth mode."
         red "  Try: CHAT_PATH=/api/chat $0 \"$TASK\""
         red "  Or check logs: gcloud run services logs tail $SERVICE --project=$PROJECT --region=$REGION"
         exit 4 ;;
  *)     red "  No HTTP response"; exit 4 ;;
esac
