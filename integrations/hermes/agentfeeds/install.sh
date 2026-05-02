#!/usr/bin/env bash
set -euo pipefail

SCRIPT="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT" ]; do
  DIR="$(cd -P "$(dirname "$SCRIPT")" && pwd)"
  SCRIPT="$(readlink "$SCRIPT")"
  [[ "$SCRIPT" != /* ]] && SCRIPT="$DIR/$SCRIPT"
done
PLUGIN_DIR="$(cd "$(dirname "$SCRIPT")" && pwd)"
REPO_ROOT="$(cd "$PLUGIN_DIR/../../.." && pwd)"

mkdir -p "$HOME/.hermes/plugins" "$HOME/.hermes/skills" "$HOME/.local/bin"

ln -sfn "$PLUGIN_DIR" "$HOME/.hermes/plugins/agentfeeds"
ln -sfn "$PLUGIN_DIR" "$HOME/.hermes/skills/agentfeeds"
ln -sfn "$PLUGIN_DIR/bin/agentfeeds" "$HOME/.local/bin/agentfeeds"
ln -sfn "$PLUGIN_DIR/bin/agentfeeds-fetch" "$HOME/.local/bin/agentfeeds-fetch"
ln -sfn "$PLUGIN_DIR/bin/agentfeeds-install-poll" "$HOME/.local/bin/agentfeeds-install-poll"
ln -sfn "$PLUGIN_DIR/bin/agentfeeds-uninstall-poll" "$HOME/.local/bin/agentfeeds-uninstall-poll"

if command -v hermes >/dev/null 2>&1; then
  hermes plugins enable agentfeeds
else
  echo "hermes not found on PATH; enable the plugin manually later: hermes plugins enable agentfeeds" >&2
fi

uv run --project "$REPO_ROOT" agentfeeds-fetch --update-catalog --regenerate-catalog

echo "Installed Agent Feeds Hermes plugin, skill, and CLI wrappers."
echo "Restart Hermes for the plugin and skill to take effect."
