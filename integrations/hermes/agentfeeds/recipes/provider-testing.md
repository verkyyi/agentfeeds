# Provider Testing Recipe

Use this after creating or editing an Agent Feeds provider.

1. Validate the stream definition:

```bash
uv run python scripts/validate-stream.py catalog/streams/<category>/<name>.yaml
```

2. Rebuild the catalog index:

```bash
uv run python scripts/build-index.py
```

3. Confirm discovery sees the provider:

```bash
agentfeeds-fetch --update-catalog
agentfeeds discover <query>
```

4. Smoke-test with a temporary Agent Feeds root instead of the user's live subscriptions:

```bash
tmp="$(mktemp -d)"
agentfeeds --root "$tmp" subscribe <provider-id> key=value --no-fetch
agentfeeds --root "$tmp" refresh <subscription-id>
agentfeeds --root "$tmp" status
sed -n '1,80p' "$tmp/catalog.md"
```

5. Inspect the generated state JSON under `$tmp/state/` and verify:
   - `_meta.subscription_id` is the concrete instance id.
   - `_meta.provider_id` is the provider id.
   - `data` matches the schema and contains only intended fields.
   - private/local sources are read-only.

6. Run the repository tests:

```bash
uv run pytest
```

Only subscribe in the user's live `~/.agentfeeds` root after the smoke test passes or the user explicitly asks to install the subscription.
