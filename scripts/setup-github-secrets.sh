#!/usr/bin/env bash
# setup-github-secrets.sh
#
# One-command bootstrap for a forked youtube-archiver repo.
# Encodes credentials.json and token.json as base64 and either:
#   (a) uploads them via the gh CLI if gh is installed and authenticated, or
#   (b) prints them for manual paste into GitHub Secrets/Variables.
#
# Usage:
#   scripts/setup-github-secrets.sh [--credentials-file PATH] [--token-file PATH]
#
# Prerequisites:
#   1. Run `youtube-archiver auth setup` first to generate token.json.
#   2. Have credentials.json from Google Cloud Console.
#   3. (Optional) Install gh CLI and run `gh auth login` for the automated path.
#
# See docs/fork-setup.md for the full setup guide.

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
CREDENTIALS_FILE="${CREDENTIALS_FILE:-credentials.json}"
TOKEN_FILE="${TOKEN_FILE:-token.json}"

# ── Arg parsing ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --credentials-file) CREDENTIALS_FILE="$2"; shift 2 ;;
    --token-file)       TOKEN_FILE="$2";        shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \?//' | head -20
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
bold()    { printf '\033[1m%s\033[0m' "$*"; }
green()   { printf '\033[32m%s\033[0m' "$*"; }
yellow()  { printf '\033[33m%s\033[0m' "$*"; }
red()     { printf '\033[31m%s\033[0m' "$*"; }
cyan()    { printf '\033[36m%s\033[0m' "$*"; }

divider() { printf '\n%s\n' "────────────────────────────────────────────────────"; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo ""
echo "$(bold 'YouTube Archiver — GitHub Secrets Setup')"
divider

MISSING=0
if [[ ! -f "$CREDENTIALS_FILE" ]]; then
  echo "$(red '✗') credentials.json not found at: $CREDENTIALS_FILE"
  echo "  Download it from Google Cloud Console → APIs & Services → Credentials"
  MISSING=1
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "$(red '✗') token.json not found at: $TOKEN_FILE"
  echo "  Run: $(cyan 'youtube-archiver auth setup') to generate it"
  MISSING=1
fi

if [[ $MISSING -eq 1 ]]; then
  echo ""
  echo "$(red 'Aborting.') Fix the above issues and re-run this script."
  exit 1
fi

echo "$(green '✓') Found credentials.json: $CREDENTIALS_FILE"
echo "$(green '✓') Found token.json:       $TOKEN_FILE"

# ── Base64 encode ─────────────────────────────────────────────────────────────
CREDS_B64=$(base64 < "$CREDENTIALS_FILE" | tr -d '\n')
TOKEN_B64=$(base64 < "$TOKEN_FILE"       | tr -d '\n')

# ── Detect gh CLI ─────────────────────────────────────────────────────────────
USE_GH=0
if command -v gh &>/dev/null; then
  if gh auth status &>/dev/null 2>&1; then
    USE_GH=1
  fi
fi

# ── Upload or print ───────────────────────────────────────────────────────────
if [[ $USE_GH -eq 1 ]]; then
  divider
  echo ""
  echo "$(bold 'gh CLI detected — uploading secrets automatically...')"
  echo ""

  printf '%s' "$CREDS_B64" | gh secret set YOUTUBE_CREDENTIALS_JSON --body -
  echo "$(green '✓') Secret set: YOUTUBE_CREDENTIALS_JSON"

  printf '%s' "$TOKEN_B64" | gh secret set YOUTUBE_TOKEN_JSON --body -
  echo "$(green '✓') Secret set: YOUTUBE_TOKEN_JSON"

  divider
  echo ""
  echo "$(bold 'Now set the required Variable for your ward channel:')"
  echo ""
  echo "  Your channel ID is the 24-character ID starting with UC."
  echo "  Find it: YouTube Studio → Settings → Channel → Advanced settings"
  echo ""
  printf '  Channel ID (UCxxxxxxxxxxxxxxxxxxxxxxxxx): '
  read -r CHANNEL_ID

  if [[ -n "$CHANNEL_ID" ]]; then
    gh variable set WARD_CHANNEL_ID --body "$CHANNEL_ID"
    echo "$(green '✓') Variable set: WARD_CHANNEL_ID = $CHANNEL_ID"
  else
    echo "$(yellow '⚠') Skipped WARD_CHANNEL_ID — set it manually in repo Settings → Variables."
  fi

  echo ""
  echo "$(bold 'Optional Variables') (press Enter to skip any):"
  echo ""

  for var in WARD_NAME STAKE_NAME TECH_SPECIALIST WARD_TIMEZONE TARGET_VISIBILITY; do
    printf "  %s: " "$var"
    read -r VAL
    if [[ -n "$VAL" ]]; then
      gh variable set "$var" --body "$VAL"
      echo "  $(green '✓') $var = $VAL"
    fi
  done

  divider
  echo ""
  echo "$(green '✓ All done!')"
  echo ""
  echo "Next steps:"
  echo "  1. $(cyan 'Trigger the workflow manually first (dry run):')"
  echo "     GitHub → Actions → Archive Live Broadcasts → Run workflow (dry_run = true)"
  echo "  2. Verify the log shows the right videos."
  echo "  3. Run again with dry_run = false."
  echo "  4. The cron (Tue/Fri 05:00 UTC) takes over automatically."

else
  # ── Manual fallback ──────────────────────────────────────────────────────
  divider
  echo ""
  echo "$(yellow 'gh CLI not found or not authenticated — printing values for manual paste.')"
  echo ""
  echo "Install gh: https://cli.github.com/  OR paste the values below manually."
  echo ""
  echo "Go to: $(cyan 'github.com/<your-fork>/settings/secrets/actions')"
  echo "Click 'New repository secret' for each of the following:"
  divider

  echo ""
  echo "$(bold 'Secret 1: YOUTUBE_CREDENTIALS_JSON')"
  echo "$CREDS_B64"
  echo ""

  echo "$(bold 'Secret 2: YOUTUBE_TOKEN_JSON')"
  echo "$TOKEN_B64"
  echo ""

  divider
  echo ""
  echo "Then go to: $(cyan 'github.com/<your-fork>/settings/variables/actions')"
  echo "Click 'New repository variable' and add:"
  echo ""
  echo "  $(bold 'WARD_CHANNEL_ID') = <your 24-char YouTube channel ID>"
  echo "  (Optional) WARD_NAME, STAKE_NAME, TECH_SPECIALIST, WARD_TIMEZONE, TARGET_VISIBILITY"
  echo ""
  divider
  echo ""
  echo "After setting secrets and variables, trigger a dry-run:"
  echo "  GitHub → Actions → Archive Live Broadcasts → Run workflow (dry_run = true)"
fi
