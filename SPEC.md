# Agent Feeds — Implementation Spec

**Version:** 0.3-internal
**Status:** Working draft for reference implementation
**Audience:** The agent (Hermes, Claude Code, etc.) implementing the bundle and reference fetcher
**Goal:** Build a working agentskills bundle + catalog + fetcher that gives a personal AI agent ambient awareness of external data streams via local files.

-----

## 0. What you’re building

A repository (working name: `agentfeeds`) containing:

1. **The skills bundle** — markdown files an agent runtime loads to learn the protocol.
1. **A starter catalog** — YAML stream definitions wrapping existing free APIs.
1. **A fetcher** — a Python script that reads subscriptions, runs adapters, writes state files.
1. **An interop spec** — this document, plus the schemas it references.

Users install the bundle. Their agent reads the catalog when asked, subscribes to streams, the fetcher polls (lazily by default, via cron if opted-in), and state files appear in `~/.agentfeeds/state/`. The agent reads those files instead of doing web searches.

-----

## 1. Repository Layout

```
agentfeeds/
├── SPEC.md                          # this document
├── README.md                        # human-facing intro
├── LICENSE                          # MIT
├── bundle/                          # the agentskills bundle users install
│   ├── SKILL.md                     # primary skill, always loaded
│   ├── recipes/
│   │   ├── subscribe.md             # how the agent subscribes to a stream
│   │   ├── unsubscribe.md           # how the agent removes a subscription
│   │   ├── refresh.md               # how the agent refreshes a stream now
│   │   └── discover.md              # how the agent searches the catalog
│   └── bin/
│       ├── agentfeeds-fetch         # fetcher entrypoint (Python)
│       └── agentfeeds-install-poll  # optional cron/launchd installer
├── catalog/                         # curated stream definitions
│   ├── INDEX.json                   # auto-generated, agent-readable catalog of streams
│   ├── streams/
│   │   ├── weather/
│   │   │   ├── openmeteo-current.yaml
│   │   │   └── nws-alerts.yaml
│   │   ├── dev/
│   │   │   ├── github-releases.yaml
│   │   │   └── hackernews-frontpage.yaml
│   │   ├── geo/
│   │   │   └── usgs-earthquakes.yaml
│   │   └── ...
│   └── schemas/
│       ├── envelope.v0.3.json
│       ├── stream-definition.v0.3.json
│       └── event-types/
│           ├── weather.observation.v1.json
│           ├── github.release.v1.json
│           └── ...
├── tests/
│   ├── fixtures/                    # recorded API responses for offline tests
│   ├── test_fetcher.py
│   ├── test_adapters.py
│   └── test_catalog_validity.py
└── scripts/
    ├── build-index.py               # regenerates catalog/INDEX.json from streams/
    └── validate-stream.py           # validates a single stream definition
```

-----

## 2. User-facing directory layout (created on first use)

```
~/.agentfeeds/
├── subscriptions.yaml               # source of truth for active subscriptions
├── catalog.md                       # always-loaded metadata for the agent
├── catalog-cache/                   # local cache of the public catalog (refreshed weekly)
│   └── INDEX.json
├── providers/                       # user-local provider pack
│   ├── streams/                     # custom provider YAML
│   └── schemas/
│       └── event-types/             # custom event schemas
└── state/                           # state files, one per subscription
    ├── weather.gov/
    │   └── forecast.lat=37.33,lon=-121.89.json
    └── github.com/
        └── repos.anthropics.claude-code.releases.json
```

The `~/.agentfeeds/` root is created by the `subscribe` recipe on first use. It is the only place the bundle writes to.

Built-in providers ship in the repo catalog. User-local providers live under `~/.agentfeeds/providers/` and are merged into discovery at runtime. Local provider IDs must not conflict with built-in provider IDs.

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

## 5. Catalog Format (always-loaded metadata)

`~/.agentfeeds/catalog.md` is the always-loaded summary the agent reads at session start. It is regenerated by the fetcher whenever subscriptions or state files change.

Format (markdown, agent-readable):

```markdown
# Agent Feeds — Active Subscriptions

This file lists data streams currently subscribed. Detailed state lives in `state/<...>.json`. Read those files when the user asks about the relevant topic.

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
*Last regenerated: 2026-05-01T12:04:00Z. Agent: when the user asks about a topic above, read the corresponding state file. Do not web-search if a non-stale state file covers the question.*
```

The closing italic line is intentional — it instructs the agent on intended use.

-----

## 6. Subscription Configuration

`~/.agentfeeds/subscriptions.yaml` is the durable record. The fetcher reads it; the agent edits it via the `subscribe`/`unsubscribe` recipes.

```yaml
version: "0.3"
defaults:
  poll_interval_seconds: 600
  history_limit: 50
subscriptions:
  - id: weather/san-jose-current    # concrete active subscription id
    title: San Jose current weather
    provider: weather/openmeteo-current
    parameters:
      lat: 37.33
      lon: -121.89
    poll_interval_seconds: 600       # optional override
  - id: dev/anthropics-claude-code-releases
    title: anthropics/claude-code releases
    provider: dev/github-releases
    parameters:
      owner: anthropics
      repo: claude-code
    poll_interval_seconds: 3600
  - id: geo/usgs-earthquakes-hour
    title: USGS earthquakes in the past hour
    provider: geo/usgs-earthquakes-hour
    filter:
      data.magnitude: { gte: 4.0 }
```

The fetcher resolves each `provider` against the catalog cache to get the full stream definition. `id` is the concrete active subscription identity that agents see. Providers/templates are used for discovery and subscription; only active subscription instances are injected into prompts.

When subscribing to a provider with parameters, materialize it into a concrete instance. `agentfeeds subscribe` may derive the `id` and `title`, or the user can pass `--id` and `--title`. Providers without parameters can use the provider id/title as the concrete instance because there is only one natural instance.

-----

## 7. Stream Definition Format (catalog entries)

Each file under `catalog/streams/` or `~/.agentfeeds/providers/streams/` is a YAML stream definition.

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

`catalog/INDEX.json` is auto-generated by `scripts/build-index.py`. Lightweight, agent-readable, designed to be the file the agent searches when discovering streams.

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

## 8. The Fetcher (`bundle/bin/agentfeeds-fetch`)

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
- Resolve the stream definition by `provider`.
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
1. Regenerate `~/.agentfeeds/catalog.md`.

### 8.3 Error handling

- HTTP errors: log to stderr, continue with other subscriptions, do NOT touch the existing state file. Stale data is better than wiped data.
- Schema validation failures (when enabled): log, skip writing, continue.
- Adapter config errors: surfaced loudly, may exit non-zero so cron logs alert the user.

### 8.4 No background daemon mode in v0.3

The fetcher is a one-shot script. Polling is achieved by cron/launchd invoking it on schedule. No long-running process. This is deliberate — keeps the implementation simple, makes failures debuggable, avoids state daemon issues.

-----

## 9. The Bundle (`bundle/SKILL.md` and recipes)

The primary user experience is agent-orchestrated. The user asks for outcomes in natural language; the agent uses `agentfeeds` and `agentfeeds-fetch` as an internal control plane, then reports results. The CLI exists for agents, scripts, and debugging, not as the normal operator workflow.

### 9.1 SKILL.md (always loaded)

Must teach the agent these behaviors:

1. **At session start:** Read `~/.agentfeeds/catalog.md` if it exists. Treat the listed streams as available context.
1. **When user asks about a topic covered by a subscribed stream:** Read the corresponding state file directly. Do not web-search if a non-stale state file covers the question.
1. **When the user asks to subscribe to something:** Load `recipes/subscribe.md` and follow it.
1. **When state appears stale and the user asks about it:** Run `agentfeeds-fetch --stream <subscription-id>` to refresh, then re-read.
1. **When the user asks what’s available:** Load `recipes/discover.md` to search the catalog.
1. **When no provider fits:** Offer to draft a provider and validate it before touching the live subscription root.

The SKILL.md should be 80-150 lines. It is always in context, so it must be terse.

### 9.2 Recipes (loaded on demand)

**`recipes/subscribe.md`** — agent flow:

1. Determine what the user wants ambient context about.
1. Search `~/.agentfeeds/catalog-cache/INDEX.json` for matching streams (by tags, type, description).
1. If multiple matches, pick the highest-quality (`verified` > `community` > `experimental`) and prefer `auth: none`.
1. Identify required parameters from the stream definition.
1. Fill parameters from user input (geocode locations, look up tickers, etc.).
1. Append the materialized subscription instance to `~/.agentfeeds/subscriptions.yaml`.
1. Run `agentfeeds-fetch --once <subscription-id>` for eager first-fetch.
1. Confirm to user with a quick read of the new state file.

**`recipes/unsubscribe.md`** — remove from `subscriptions.yaml`, delete state file, run `--regenerate-catalog`.

**`recipes/refresh.md`** — run `agentfeeds-fetch --stream <subscription-id>` or `agentfeeds-fetch --all`.

**`recipes/discover.md`** — search the catalog INDEX, present matches to the user, suggest which to subscribe to.

**`recipes/provider-authoring.md`** — draft user-local provider YAML under `~/.agentfeeds/providers/streams/` and schemas under `~/.agentfeeds/providers/schemas/event-types/`.

**`recipes/provider-testing.md`** — run `agentfeeds providers validate`, confirm discovery, and smoke-test with a temporary Agent Feeds root before subscribing in the live root.

Provider authoring helpers:

```
agentfeeds providers adapters
agentfeeds providers scaffold <adapter-kind> <provider-id>
agentfeeds providers validate
```

`local_command` is argv-only and intended for explicitly approved read commands. In `snapshot` mode it captures stdout/stderr with a timeout and output cap, and may parse stdout as JSON before applying a JMESPath transform. In `event` mode it requires `parse: json`, selects an item array with `items_from`, optionally uses `id_from` and `time_from`, and applies the transform to each item.

-----

## 10. Polling Installer (`bundle/bin/agentfeeds-install-poll`)

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

- Have a valid YAML definition under `catalog/streams/`.
- Have a JSON Schema under `catalog/schemas/event-types/`.
- Pass `scripts/validate-stream.py`.
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

`tests/test_catalog_validity.py`:

- Every YAML in `catalog/streams/` parses, validates against `stream-definition.v0.3.json`.
- Every referenced schema URL resolves to a parseable JSON Schema.
- Every adapter config can be dry-run (config-validated without making network calls).

`scripts/validate-stream.py` is the single-stream version of the catalog validity test, used by contributors and CI.

-----

## 13. Implementation Order

Build in this order. Each step depends on the previous one being functional.

1. **Schemas** — `envelope.v0.3.json`, `stream-definition.v0.3.json`. Establishes the contracts.
1. **Fetcher core** — load subscriptions, run a single hardcoded `json_http` adapter against Open-Meteo, write a state file. End-to-end skeleton.
1. **Adapter kinds** — generalize the fetcher to support all four adapter kinds.
1. **State merging** — implement snapshot, event, and delta merge logic with tests.
1. **Catalog regeneration** — generate `~/.agentfeeds/catalog.md` from current state files.
1. **Starter catalog** — write the 8 stream definitions and their schemas, with fixtures.
1. **Bundle SKILL.md and recipes** — write the agentskills bundle.
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
- [ ] `~/.agentfeeds/catalog.md` regenerates correctly after each fetch.
- [ ] The bundle’s `SKILL.md` + recipes work in Hermes: subscribe, unsubscribe, refresh, discover all complete without error.
- [ ] At least one full end-to-end demo works: cold install → `subscribe me to weather in San Jose` → state file exists → user asks “what’s the weather?” → agent reads state file (no web search) → correct answer.
- [ ] Hermes can translate operator intent into Agent Feeds actions without requiring the operator to know CLI flags.
- [ ] Hermes can draft and validate a user-local provider under `~/.agentfeeds/providers/` without modifying the built-in catalog.
- [ ] All tests in `tests/` pass.
- [ ] README explains install, basic usage, and how to contribute a stream.
- [ ] Your own Hermes setup has been running this for at least 7 days without intervention.

-----

## 16. Quick Reference for the Implementing Agent

When in doubt:

- **State files are read-only from the agent’s perspective.** Never write to `state/` from a recipe.
- **Subscription changes go through `subscriptions.yaml`.** The fetcher picks them up automatically; no daemon to restart.
- **Filenames follow §4.1 exactly.** Don’t invent paths.
- **Atomic writes always.** Every state file write is `tmp + fsync + rename`.
- **One adapter kind at a time.** Get `json_http` working end-to-end before starting `rss`.
- **The catalog.md is the agent’s primary view.** If it’s not regenerating correctly after a fetch, that’s a P0 bug.
- **Lazy by default.** Don’t add background daemons. Cron is the only acceptable polling mechanism.

When you finish a step in §13, commit. Small commits, message format: `step N: <what>`.

-----

*End of spec. If something here is ambiguous, surface it as a question rather than guessing — the cost of asking is lower than the cost of inconsistent implementation.*
