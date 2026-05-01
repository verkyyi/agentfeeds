# Subscribe Recipe

Use this when the user asks to subscribe to an ambient data stream.

1. Determine the topic the user wants covered.
2. Search `~/.agentfeeds/catalog-cache/INDEX.json` for matching streams by `id`, `type`, `tags`, `title`, and `description`.
3. If the cache is missing, run `agentfeeds-fetch --update-catalog`.
4. Prefer streams in this order:
   - `quality_tier: verified`
   - `auth: none`
   - closest parameter fit to the user's request
5. Load the matching stream YAML from the catalog cache or bundled catalog.
6. Fill all required parameters from the user's request.
7. Create `~/.agentfeeds/subscriptions.yaml` if missing.
8. Append the subscription entry.
9. Run `agentfeeds-fetch --once <stream-id>` for an eager first fetch.
10. Read the new state file and confirm the subscription with a concise summary.

Do not write directly to `~/.agentfeeds/state/`.
