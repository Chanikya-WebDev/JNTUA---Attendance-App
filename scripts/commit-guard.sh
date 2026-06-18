#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX_FILE="${ROOT_DIR}/templates/index.html"
OUTPUT_CSS="${ROOT_DIR}/static/css/output.css"
PACKAGE_JSON="${ROOT_DIR}/package.json"

error() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || error "Missing required file: $1"
}

require_pattern() {
  local file="$1"
  local pattern="$2"
  local label="$3"

  if ! grep -Eiq "$pattern" "$file"; then
    error "Missing required ${label} in ${file}"
  fi
}

forbid_env_files() {
  local tracked staged

  # Find all .env* files except .env.example
  tracked="$(git -C "$ROOT_DIR" ls-files | grep -E '(^|/)\.env(\..*)?$' | grep -v '\.env\.example$' || true)"
  if [[ -n "$tracked" ]]; then
    printf 'Tracked .env files detected (excluding .env.example):\n%s\n' "$tracked" >&2
    exit 1
  fi

  staged="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACM | grep -E '(^|/)\.env(\..*)?$' | grep -v '\.env\.example$' || true)"
  if [[ -n "$staged" ]]; then
    printf 'Staged .env files detected (excluding .env.example):\n%s\n' "$staged" >&2
    exit 1
  fi
}

build_tailwind() {
  if [[ ! -f "$PACKAGE_JSON" ]]; then
    echo "No package.json found; skipping Tailwind build."
    return 0
  fi

  command -v npm >/dev/null 2>&1 || error "npm is required to build Tailwind CSS"

  # Check if tailwindcss is installed locally
  if [[ ! -f "$ROOT_DIR/node_modules/.bin/tailwindcss" ]]; then
    error "tailwindcss is not installed. Please run 'npm install' to install dependencies."
  fi

  echo "Building Tailwind CSS..."
  (cd "$ROOT_DIR" && npm run build-css)

  [[ -f "$OUTPUT_CSS" ]] || error "Tailwind build did not produce static/css/output.css"
}

main() {
  require_file "$INDEX_FILE"
  forbid_env_files

  require_pattern "$INDEX_FILE" 'google-site-verification' 'Google Search Console verification tag'
  require_pattern "$INDEX_FILE" '(googletagmanager|google-analytics|gtag\()' 'Google Analytics tag'

  build_tailwind

  echo "Commit guard passed."
}

main "$@"