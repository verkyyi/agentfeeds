# Provider Authoring Recipe

Use this when the user wants Agent Feeds to support a source that no current provider covers.

1. Run `agentfeeds discover <query>` and confirm no existing provider fits.
2. Run `agentfeeds providers adapters` and classify the source:
   - `local_file` for one local text, Markdown, or JSON file.
   - `json_http` for one HTTP JSON snapshot.
   - `paginated_json_http` for HTTP JSON event lists.
   - `rss` for RSS or Atom feeds.
   - `ical` for calendar feeds.
3. Pick a provider id in `category/name` form. Prefer personal/local categories for private sources, such as `local/...` or `personal/...`.
4. Pick the mode:
   - `snapshot` for one current state.
   - `event` for a list of recent items.
5. Define required parameters. Do not bake user-specific secrets into provider YAML.
6. Run `agentfeeds providers scaffold <adapter-kind> <provider-id>`.
7. Edit the generated YAML under `~/.agentfeeds/providers/streams/<category>/<name>.yaml`.
8. Edit the generated schema under `~/.agentfeeds/providers/schemas/event-types/<type>.v1.json` when the scaffold created one.
9. Reuse built-in schemas for `rss` and `ical` unless the user needs custom fields.
10. Keep provider descriptions short and operator-facing. Include tags that help `agentfeeds discover`.
11. Run `recipes/provider-testing.md`.

For local/private sources, prefer read-only snapshots. Provider adapters should read from the source and write Agent Feeds state; they should not mutate the original source.

Minimal stream template, equivalent to `agentfeeds providers scaffold local_file local/example`:

```yaml
id: local/example
title: Example local source
description: Read-only snapshot of example local data.
type: local.example
mode: snapshot
schema_url: https://agentfeeds.dev/schemas/local.example.v1.json
schema_version: 1.0.0
parameters:
  - name: path
    type: string
    description: Absolute or home-relative file path
    required: true
source_uri_template: "feed://local.example/source?path={path}"
adapter:
  kind: local_file
  path: "{path}"
recommended_poll_interval_seconds: 300
auth: none
tags: [local, private, no-auth]
quality_tier: verified
contributed_by: agentfeeds
```
