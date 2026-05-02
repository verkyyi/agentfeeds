# Subscribe Recipe

Use this when the user asks to subscribe to an ambient data stream.

1. Determine the topic the user wants covered.
2. Search `~/.agentfeeds/catalog-cache/INDEX.json` for matching streams by `id`, `type`, `tags`, `title`, and `description`.
3. If the cache is missing, run `agentfeeds-fetch --update-catalog`.
4. Prefer streams in this order:
   - `quality_tier: verified`
   - `auth: none`
   - closest parameter fit to the user's request
5. Fill all required parameters from the user's request.
6. Run `agentfeeds subscribe <provider-id> key=value ...`.
7. If the user supplied a preferred name, pass `--id <subscription-id>` and/or `--title "<title>"`.
8. Read the new state file and confirm the concrete subscription id with a concise summary.

For local files, use `agentfeeds subscribe local/file path=<path>`. Local file subscriptions are read-only snapshots; do not edit the source file or hand-write files in `~/.agentfeeds/state/`.

Do not write directly to `~/.agentfeeds/state/`.
