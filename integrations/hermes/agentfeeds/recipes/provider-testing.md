# Provider Testing Recipe

Use this after creating or editing an Agent Feeds provider.

1. Validate the stream definition:

```bash
agentfeeds providers validate
```

2. Run the provider once without writing state or touching subscriptions:

```bash
agentfeeds providers test <provider-id> key=value
agentfeeds providers test <provider-id> key=value --json
```

3. Confirm discovery sees the provider:

```bash
agentfeeds discover <query>
```

4. If you need to test subscription materialization, use a temporary Agent Feeds root instead of the user's live subscriptions. Copy the drafted local provider tree into the temp root first:

```bash
tmp="$(mktemp -d)"
mkdir -p "$tmp/providers"
cp -R ~/.agentfeeds/providers/streams "$tmp/providers/"
cp -R ~/.agentfeeds/providers/schemas "$tmp/providers/"
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

Only subscribe in the user's live `~/.agentfeeds` root after the smoke test passes or the user explicitly asks to install the subscription.
