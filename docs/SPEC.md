# Agent Feeds — Implementation Spec

**Version:** 0.3-internal
**Status:** Working draft for reference implementation
**Audience:** The agent (Hermes, Claude Code, etc.) implementing the reference fetcher, catalog, and integrations
**Goal:** Build a working catalog + fetcher that gives a personal AI agent ambient awareness of external data streams via local files.

-----

## 0. What you’re building

A repository (working name: `agentfeeds`) containing:

1. **A starter catalog** — YAML stream definitions wrapping existing free APIs.
1. **A fetcher** — a Python script that reads subscriptions, runs adapters, writes state files.
1. **An interop spec** — this document, plus the schemas it references.

Users install an agent integration, such as the standalone Hermes plugin at `agentfeeds-hermes-plugin`. Their agent reads the catalog when asked, subscribes to streams, the fetcher polls (lazily by default, via cron if opted-in), and state files appear in `~/.agentfeeds/state/`. The agent reads those files instead of doing web searches.

-----

## 1. Repository Layout

```
agentfeeds/
├── README.md                        # human-facing intro
├── LICENSE                          # MIT
├── docs/
│   └── SPEC.md                      # this document
├── agentfeeds/                      # Python package and CLI entrypoints
│   ├── constants.py                 # shared runtime constants
│   ├── commands.py                  # management CLI and command handlers
│   ├── fetcher.py                   # reference fetcher orchestration
│   ├── adapters/
│   │   ├── http.py
│   │   ├── rss.py
│   │   ├── ical.py
│   │   ├── local_file.py
│   │   └── local_command.py
│   └── polling/
│       ├── install.py               # optional cron/launchd installer
│       └── uninstall.py             # optional cron/launchd uninstaller
└── tests/
    ├── fixtures/                    # recorded API responses for offline tests
    ├── test_fetcher.py
    ├── test_adapters.py
    └── test_catalog_validity.py
```

Built-in template definitions live in the separate `agentfeeds-catalog` repository:

```
agentfeeds-catalog/
├── catalog/
│   ├── INDEX.json
│   ├── streams/
│   └── schemas/
└── scripts/
    ├── build-index.py
    └── validate-stream.py
```

-----

## 2. Runtime storage layout (created on first use)

```
~/.agentfeeds/
├── subscriptions.yaml               # source of truth for active subscriptions
├── catalog.md                       # inspection/fallback active-stream metadata
├── catalog-cache/                   # local cache of the public catalog (refreshed weekly)
│   └── INDEX.json
├── templates/                       # user-local template pack
│   ├── streams/                     # custom template YAML
│   └── schemas/
│       └── event-types/             # custom event schemas
└── state/                           # state files, one per subscription
    ├── weather.gov/
    │   └── forecast.lat=37.33,lon=-121.89.json
    └── github.com/
        └── repos.anthropics.claude-code.releases.json
```

The `~/.agentfeeds/` root is created by the CLI on first use. It is the only place Agent Feeds writes runtime state. Agent integrations should treat this layout as an implementation detail and prefer CLI commands for normal operation. Paths may be surfaced for debugging and template authoring, but they should not be required ambient context.

Built-in templates ship in the `agentfeeds-catalog` repo and are cached under `~/.agentfeeds/catalog-cache/`. User-local templates live under `~/.agentfeeds/templates/` and are merged into discovery at runtime. Local template IDs must not conflict with built-in template IDs.

-----

## 3. Event Envelope (canonical shape on disk and over the wire)

Every event, whether produced by an adapter or read from a state file, conforms to this envelope. CloudEvents-aligned where reasonable.

```json
{
  "specversion": "agentfeeds/0.3",
  "id": "string (unique within stream, monotonic preferred)",
  "source": "feed://host/path[?params]",
  "type": "string (e.g. 'weather.observation', 'github.release')",
  "time": "RFC 3339 UTC",
  "schema_url": "https://... (URL to JSON Schema for `data`)",
  "schema_version": "semver",
  "mode": "snapshot | event | delta",
  "data": { ... }
}
```

|Field           |Required|Notes                                                                                                                                           |
|----------------|--------|------------------------------------------------------------------------------------------------------------------------------------------------|
|`specversion`   |yes     |Always `"agentfeeds/0.3"` for this version.                                                                                                     |
|`id`            |yes     |Unique within the stream. For `snapshot`, can be derived from `time`. For `event`, MUST be stable per upstream entity (e.g. GitHub release tag).|
|`source`        |yes     |The stream URI. Same value for every event in a stream.                                                                                         |
|`type`          |yes     |Stable per stream. Used by the agent to reason about kind.                                                                                      |
|`time`          |yes     |When the event was produced.                                                                                                                    |
|`schema_url`    |yes     |URL to the JSON Schema for `data`.                                                                                                              |
|`schema_version`|yes     |Schema’s semver.                                                                                                                                |
|`mode`          |yes     |Must match the stream’s declared mode.                                                                                                          |
|`data`          |yes     |The payload. MUST validate against `schema_url` if validation is enabled.                                                                       |

**Stream URI format:** `feed://<host>/<path>[?<query>]`. Used as the canonical identifier.

-----

## 4. State File Format

State files are what the agent reads. Always JSON. Always have the same top-level shape:

```json
{
  "_meta": {
    "stream": "feed://...",
    "type": "weather.observation",
    "mode": "snapshot",
    "last_updated": "2026-05-01T12:00:00Z",
    "next_poll_due": "2026-05-01T12:05:00Z",
    "schema_url": "https://...",
    "schema_version": "1.0.0",
    "publisher": "weather.gov",
    "stale": false
  },
  "data": ...
}
```

`_meta.stale` is `true` when `now - last_updated > 2 × poll_interval`. The fetcher computes and writes this.

`data` shape depends on `mode`:

- **`snapshot`** — `data` is the latest event’s `data` object directly.
- **`event`** — `data` is an array of recent events (full envelope objects), newest first, capped at the subscription’s `history_limit` (default 50).
- **`delta`** — `data` is the reconstructed current state. Individual deltas are not exposed.

### 4.1 Filename derivation (deterministic, normative)

Given stream URI `feed://<host>/<path>[?<query>]`:

1. Strip the `feed://` scheme.
1. The host becomes the first directory under `state/`.
1. Path segments join with `.` (dot). Leading slashes dropped.
1. If query present: append `.` then query string with `&` replaced by `,`.
1. Append `.json`.

Examples:

- `feed://weather.gov/forecast?lat=37.33&lon=-121.89` → `state/weather.gov/forecast.lat=37.33,lon=-121.89.json`
- `feed://github.com/repos/anthropics/claude-code/releases` → `state/github.com/repos.anthropics.claude-code.releases.json`
- `feed://earthquake.usgs.gov/all/hour` → `state/earthquake.usgs.gov/all.hour.json`

This rule is reversible. Any conformant implementation produces the same path.

### 4.2 Atomic writes

State files MUST be written atomically:

1. Write to `<final-path>.tmp`
1. `fsync` the temp file
1. `rename(tmp, final-path)` — atomic on POSIX

Never write partial files. The agent may read at any time without coordination.

-----

## 5. Active Stream Map

The primary agent-facing active stream map is the `agentfeeds streams` command group. It keeps agents from depending on storage paths during normal operation:

```
agentfeeds streams list --json
agentfeeds streams search <topic> --json
agentfeeds streams show <subscription-id> --json
agentfeeds streams read <subscription-id> --json
```

`~/.agentfeeds/catalog.md` is still regenerated by the fetcher for human inspection and emergency fallback when the CLI is unavailable. It is not the preferred prompt surface.

Fallback format:

```markdown
# Agent Feeds — Active Subscriptions

This file lists data streams currently subscribed. Prefer `agentfeeds streams read <subscription-id> --json` for normal agent access.

## weather.observation — San Jose, CA
- **Stream:** `feed://api.open-meteo.com/v1/forecast?latitude=37.33&longitude=-121.89`
- **Path:** `state/api.open-meteo.com/v1.forecast.latitude=37.33,longitude=-121.89.json`
- **Updated:** 2026-05-01T12:00:00Z (4 minutes ago)
- **Stale:** no
- **Mode:** snapshot

## github.release — anthropics/claude-code
- **Stream:** `feed://api.github.com/repos/anthropics/claude-code/releases`
- **Path:** `state/api.github.com/repos.anthropics.claude-code.releases.json`
- **Updated:** 2026-05-01T11:37:00Z (27 minutes ago)
- **Stale:** no
- **Mode:** event

---
*Last regenerated: 2026-05-01T12:04:00Z.*
```

The fallback file intentionally remains compact and inspectable, but it should not replace the CLI for normal agent workflows.

-----

## 6. Subscription Configuration

`~/.agentfeeds/subscriptions.yaml` is the durable record. The fetcher reads it; agents update it through `agentfeeds subscribe` and `agentfeeds unsubscribe`.

```yaml
version: "0.3"
defaults:
  poll_interval_seconds: 600
  history_limit: 50
subscriptions:
  - id: weather/san-jose-current    # concrete active subscription id
    title: San Jose current weather
    template: weather/openmeteo-current
    parameters:
      lat: 37.33
      lon: -121.89
    poll_interval_seconds: 600       # optional override
  - id: dev/anthropics-claude-code-releases
    title: anthropics/claude-code releases
    template: dev/github-releases
    parameters:
      owner: anthropics
      repo: claude-code
    poll_interval_seconds: 3600
  - id: geo/usgs-earthquakes-hour
    title: USGS earthquakes in the past hour
    template: geo/usgs-earthquakes-hour
    filter:
      data.magnitude: { gte: 4.0 }
```

The fetcher resolves each subscription's `template` field against the catalog cache to get the full stream definition. `id` is the concrete active subscription identity that agents see. Templates are used for discovery and subscription; only active subscription instances are injected into prompts.

When subscribing to a template with parameters, materialize it into a concrete instance. `agentfeeds subscribe` may derive the `id` and `title`, or the user can pass `--id` and `--title`. Parameterless templates can use the template id/title as the concrete instance because there is only one natural instance.

-----

## 7. Stream Definition Format (catalog entries)

Each file under `agentfeeds-catalog/catalog/streams/` or `~/.agentfeeds/templates/streams/` is a YAML stream definition.

```yaml
id: weather/openmeteo-current
title: Current weather conditions (Open-Meteo)
description: Free, no-API-key weather observations for any lat/lon. 10-minute resolution.
type: weather.observation
mode: snapshot
schema_url: https://agentfeeds.dev/schemas/weather.observation.v1.json
schema_version: 1.0.0

parameters:
  - name: lat
    type: number
    description: Latitude (-90 to 90)
    required: true
  - name: lon
    type: number
    description: Longitude (-180 to 180)
    required: true

source_uri_template: "feed://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"

adapter:
  kind: json_http
  url: "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
  method: GET
  headers: {}
  transform:
    language: jmespath
    expression: |
      {
        temperature_c: current.temperature_2m,
        humidity_pct: current.relative_humidity_2m,
        wind_kph: current.wind_speed_10m,
        conditions_code: current.weather_code,
        observed_at: current.time
      }
  id_from: "joined(['-', [current.time, to_string(latitude), to_string(longitude)]])"

recommended_poll_interval_seconds: 600
auth: none

tags: [weather, free, no-auth, global]
quality_tier: verified
contributed_by: lee
```

### 7.1 Adapter kinds

|`adapter.kind`       |What it does                                                                                         |
|---------------------|-----------------------------------------------------------------------------------------------------|
|`local_file`         |Read one local text, Markdown, or JSON file and emit one snapshot.                                   |
|`local_command`      |Run an argv-only local command. Use `snapshot` to capture command output, or `event` with JSON `items_from` to emit one event per item.|
|`json_http`          |GET a URL, run a JMESPath transform on the response, emit one envelope. Use for `snapshot` streams.  |
|`paginated_json_http`|GET a URL, run a transform that yields an array, emit one envelope per item. Use for `event` streams.|
|`rss`                |Parse an RSS/Atom/JSON Feed URL, emit one envelope per entry, `mode: event`, schema = `rss-item.v1`. |
|`ical`               |Parse an iCalendar URL, emit one envelope per VEVENT, `mode: event`, schema = `ical-event.v1`.       |

Other adapter kinds (`html_scrape`, `webhook_receive`, `paginated_with_cursor`) are explicitly **out of scope for v0.3**.

### 7.2 Parameter substitution

Adapter `url`, `headers`, `body`, and `transform` strings support `{param_name}` substitution from the subscription’s `parameters`. Substitution happens at fetch time. Missing required parameters cause the subscription to fail validation at subscribe time.

### 7.3 Catalog INDEX.json

`agentfeeds-catalog/catalog/INDEX.json` is auto-generated by the catalog repo's `scripts/build-index.py`. It is lightweight and inspectable, but agents should normally search it through `agentfeeds templates search`.

```json
{
  "generated_at": "2026-05-01T12:00:00Z",
  "spec_version": "0.3",
  "stream_count": 23,
  "streams": [
    {
      "id": "weather/openmeteo-current",
      "title": "Current weather conditions (Open-Meteo)",
      "description": "Free, no-API-key weather observations for any lat/lon.",
      "type": "weather.observation",
      "mode": "snapshot",
      "tags": ["weather", "free", "no-auth", "global"],
      "parameters": ["lat", "lon"],
      "auth": "none",
      "quality_tier": "verified"
    }
  ]
}
```

-----

## 8. The Fetcher (`agentfeeds-fetch`)

A Python 3.11+ script. Single file preferred for v0.3. ~300 lines target.

### 8.1 Invocation modes

```
agentfeeds-fetch                        # default: refresh stale subscriptions
agentfeeds-fetch --all                  # refresh every subscription regardless of staleness
agentfeeds-fetch --stream <id>          # refresh one specific subscription id
agentfeeds-fetch --once <id>            # one-shot fetch, used by `subscribe` recipe for eager first-fetch
agentfeeds-fetch --regenerate-catalog   # regenerate ~/.agentfeeds/catalog.md without polling
agentfeeds-fetch --update-catalog       # refresh ~/.agentfeeds/catalog-cache/ from public catalog
```

### 8.2 Behavior

1. Load `~/.agentfeeds/subscriptions.yaml`.
1. Load `~/.agentfeeds/catalog-cache/INDEX.json` (or remote if cache is missing).
1. For each subscription:
- Resolve the stream definition by the subscription's `template` field.
- Substitute parameters into the adapter config.
- Skip if not stale (unless `--all`).
- Run the adapter, get one or more envelopes.
- Apply subscription `filter` if set.
- Validate against schema if `AGENTFEEDS_VALIDATE=1`.
- Compute the state file path (§4.1).
- Merge with existing state per `mode` (§4):
  - `snapshot`: replace.
  - `event`: prepend new envelopes, dedup by `id`, truncate to `history_limit`.
  - `delta`: apply to current reconstructed state (or pull snapshot first if base unknown).
- Write atomically.
1. Regenerate `~/.agentfeeds/catalog.md` as an inspection/fallback artifact.

### 8.3 Error handling

- HTTP errors: log to stderr, continue with other subscriptions, do NOT touch the existing state file. Stale data is better than wiped data.
- Schema validation failures (when enabled): log, skip writing, continue.
- Adapter config errors: surfaced loudly, may exit non-zero so cron logs alert the user.

### 8.4 No background daemon mode in v0.3

The fetcher is a one-shot script. Polling is achieved by cron/launchd invoking it on schedule. No long-running process. This is deliberate — keeps the implementation simple, makes failures debuggable, avoids state daemon issues.

-----

## 9. Agent Integrations

The primary user experience is agent-orchestrated. The user asks for outcomes in natural language; the agent uses `agentfeeds` and `agentfeeds-fetch` as an internal control plane, then reports results. The CLI exists for agents, scripts, and debugging, not as the normal operator workflow.

The Hermes plugin and skill live in the standalone `agentfeeds-hermes-plugin` repository. Built-in template definitions live in `agentfeeds-catalog`. This core repo owns the protocol, CLI, fetcher, local template tooling, and tests.

### 9.1 Skill Instructions

Agent-facing integrations should teach these behaviors:

1. **At session start or when local context is relevant:** Use `agentfeeds streams list` or `agentfeeds streams search <topic>` to inspect active streams.
1. **When user asks about a topic covered by a subscribed stream:** Use `agentfeeds streams read <subscription-id> --json`. Do not web-search if a non-stale stream covers the question.
1. **When the user asks to subscribe to something:** Search templates with `agentfeeds templates search <query>`, inspect candidates with `agentfeeds templates show <template-id>`, then subscribe.
1. **When state appears stale and the user asks about it:** Run `agentfeeds-fetch --stream <subscription-id>` to refresh, then re-read.
1. **When the user asks what’s available:** Use `agentfeeds templates search <query>` or `agentfeeds templates list`.
1. **When no template fits:** Offer to draft a template and validate it before touching the live subscription root.

Always-loaded skill instructions should be terse. Put template authoring, testing, and less-common workflows behind progressively loaded recipes or references.

### 9.2 Recipes (loaded on demand)

**`recipes/subscribe.md`** — agent flow:

1. Determine what the user wants ambient context about.
1. Search templates with `agentfeeds templates search <query>`.
1. If multiple matches, pick the highest-quality (`verified` > `community` > `experimental`) and prefer `auth: none`.
1. Identify required parameters from the stream definition.
1. Fill parameters from user input (geocode locations, look up tickers, etc.).
1. Run `agentfeeds subscribe <template-id> [key=value ...]`.
1. Run `agentfeeds-fetch --once <subscription-id>` for eager first-fetch.
1. Confirm to user with `agentfeeds streams read <subscription-id> --json`.

**`recipes/unsubscribe.md`** — run `agentfeeds unsubscribe <subscription-id>`.

**`recipes/refresh.md`** — run `agentfeeds-fetch --stream <subscription-id>` or `agentfeeds-fetch --all`.

**`recipes/discover.md`** — run `agentfeeds templates search`, present matches to the user, suggest which to subscribe to.

**`recipes/template-authoring.md`** — draft user-local template YAML under `~/.agentfeeds/templates/streams/` and schemas under `~/.agentfeeds/templates/schemas/event-types/`.

**`recipes/template-testing.md`** — run `agentfeeds templates validate`, `agentfeeds templates test`, confirm discovery, and smoke-test subscription materialization with a temporary Agent Feeds root before subscribing in the live root.

Template authoring helpers:

```
agentfeeds templates adapters
agentfeeds templates scaffold <adapter-kind> <template-id>
agentfeeds templates test <template-id> key=value
agentfeeds templates validate
```

`local_command` is argv-only and intended for explicitly approved read commands. In `snapshot` mode it captures stdout/stderr with a timeout and output cap, and may parse stdout as JSON before applying a JMESPath transform. In `event` mode it requires `parse: json`, selects an item array with `items_from`, optionally uses `id_from` and `time_from`, and applies the transform to each item.

-----

## 10. Polling Installer (`agentfeeds-install-poll`)

Optional. User runs once to enable background polling.

Behavior:

1. Detect platform: Linux (cron), macOS (launchd), WSL (cron), other (warn, exit).
1. Compute poll interval as `min(subscription poll intervals)`, floor 5 minutes.
1. Install a cron entry / launchd plist that runs `agentfeeds-fetch` at that interval.
1. Print confirmation and how to uninstall.

Companion script `agentfeeds-uninstall-poll` cleanly removes the cron/launchd entry.

If the user declines installation, polling simply doesn’t happen — the system works lazily, refreshing only when the agent decides a state file is stale and the conversation needs fresh data.

-----

## 11. Starter Catalog (build these first)

Ship at least these stream definitions in v0.3. Each must have working adapter config and require no auth:

1. `weather/openmeteo-current` — Open-Meteo current conditions (params: lat, lon)
1. `weather/openmeteo-forecast` — Open-Meteo 7-day forecast (params: lat, lon)
1. `geo/usgs-earthquakes-hour` — USGS earthquakes past hour (no params)
1. `dev/github-releases` — GitHub repo releases (params: owner, repo)
1. `dev/github-issues` — GitHub repo issues (params: owner, repo, state)
1. `dev/github-prs` — GitHub repo pull requests (params: owner, repo, state)
1. `dev/hackernews-frontpage` — Hacker News front page via Algolia or Firebase API (no params)
1. `space/iss-location` — Current ISS lat/lon (no params)
1. `news/rss-generic` — Wraps any RSS URL (params: url)
1. `finance/exchangerate` — exchangerate.host current rates (params: base)
1. `local/file` — Read-only snapshot of a local text/Markdown/JSON file (params: path)
1. `calendar/ics` — Public iCalendar feed (params: url)

Each must:

- Have a valid YAML definition under `agentfeeds-catalog/catalog/streams/`.
- Have a JSON Schema under `agentfeeds-catalog/catalog/schemas/event-types/`.
- Pass the catalog repo's `scripts/validate-stream.py`.
- Be tested by `tests/test_adapters.py` against a recorded fixture.

-----

## 12. Test Strategy

`tests/test_fetcher.py`:

- Snapshot mode: state file replaces correctly.
- Event mode: new events prepended, dedup by id, history_limit enforced.
- Delta mode: state reconstructed correctly (use a synthetic stream).
- Atomic write: simulated crash mid-write doesn’t corrupt existing file.
- Stale detection: `_meta.stale` set correctly given mocked clock.

`tests/test_adapters.py`:

- Each adapter kind (`json_http`, `paginated_json_http`, `rss`, `ical`) tested against recorded fixtures in `tests/fixtures/`.
- Parameter substitution tested for edge cases (URL-encoded special chars, missing params, etc.).

`tests/test_catalog_validity.py` covers core catalog-cache loading and local template conflict behavior. Full built-in template validation lives in the `agentfeeds-catalog` repo.

-----

## 13. Implementation Order

Build in this order. Each step depends on the previous one being functional.

1. **Schemas** — `envelope.v0.3.json`, `stream-definition.v0.3.json`. Establishes the contracts.
1. **Fetcher core** — load subscriptions, run a single hardcoded `json_http` adapter against Open-Meteo, write a state file. End-to-end skeleton.
1. **Adapter kinds** — generalize the fetcher to support all four adapter kinds.
1. **State merging** — implement snapshot, event, and delta merge logic with tests.
1. **Catalog regeneration** — generate `~/.agentfeeds/catalog.md` as an inspection/fallback artifact.
1. **Starter catalog** — write the 8 stream definitions and their schemas in `agentfeeds-catalog`, with fixtures.
1. **Agent integration instructions** — write/update standalone plugin skills and recipes.
1. **Polling installer** — optional cron/launchd setup.
1. **Tests** — fill in coverage to the level described in §12.
1. **Documentation** — README, contribution guide.
1. **Self-dogfooding** — install on Hermes, subscribe to 5 streams, use for a week.

Steps 1-6 are the critical path. 7-11 polish what’s already working.

-----

## 14. Out of Scope for v0.3

Do not implement these. They are future work and including them now bloats the project:

- Authentication for streams that require API keys (paid streams).
- Filter expression languages beyond the simple operators in subscriptions.
- HTML scraping adapter.
- Webhook receiver adapter.
- Native publisher manifest discovery (`/.well-known/agent-feeds.json`).
- Hosted polling service.
- Premium catalog tier.
- Multi-stream synthesized views.
- Push delivery / SSE.
- Multi-user / multi-tenant operation.
- Anything related to aInbox, tokenman, or other adjacent projects.

-----

## 15. Definition of Done for v0.3

You’re done when all of these are true:

- [ ] `agentfeeds-fetch` polls the 8 starter streams and writes valid state files.
- [ ] `agentfeeds streams list/show/read` reflects refreshed state after each fetch.
- [ ] The bundle’s `SKILL.md` + recipes work in Hermes: subscribe, unsubscribe, refresh, and template search all complete without error.
- [ ] At least one full end-to-end demo works: cold install → `subscribe me to weather in San Jose` → stream data exists → user asks “what’s the weather?” → agent reads via `agentfeeds streams read` (no web search) → correct answer.
- [ ] Hermes can translate operator intent into Agent Feeds actions without requiring the operator to know CLI flags.
- [ ] Hermes can draft and validate a user-local template under `~/.agentfeeds/templates/` without modifying the built-in catalog.
- [ ] All tests in `tests/` pass.
- [ ] README explains install, basic usage, and how to contribute a stream.
- [ ] Your own Hermes setup has been running this for at least 7 days without intervention.

-----

## 16. Quick Reference for the Implementing Agent

When in doubt:

- **State files are fetcher-owned.** Agents should use `agentfeeds streams read`; never write to `state/` from a recipe.
- **Subscription changes go through the CLI.** Use `agentfeeds subscribe` and `agentfeeds unsubscribe`.
- **Filenames follow §4.1 exactly.** Don’t invent paths.
- **Atomic writes always.** Every state file write is `tmp + fsync + rename`.
- **One adapter kind at a time.** Get `json_http` working end-to-end before starting `rss`.
- **The streams CLI is the agent’s primary view.** If it does not reflect refreshed state after a fetch, that’s a P0 bug.
- **Lazy by default.** Don’t add background daemons. Cron is the only acceptable polling mechanism.

When you finish a step in §13, commit. Small commits, message format: `step N: <what>`.

-----

*End of spec. If something here is ambiguous, surface it as a question rather than guessing — the cost of asking is lower than the cost of inconsistent implementation.*
