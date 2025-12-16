#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: ./sync.sh <workspace_path>"
  exit 1
fi

WORKSPACE_PATH="$1"

git_pull_loop() {
  while true; do
    git pull --rebase --autostash || true
    sleep 10
  done
}

git_pull_loop &
GIT_PID=$!

cleanup() {
  kill "$GIT_PID" 2>/dev/null || true
}
trap cleanup EXIT

databricks sync --watch . "$WORKSPACE_PATH"