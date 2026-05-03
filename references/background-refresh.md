# Background Refresh

Background refresh is required for normal Agent Feeds use. It keeps subscriptions warm between conversations so the agent can answer from local state instead of rerunning source-specific fetching, searching, querying, or processing on demand.

Check scheduler status:

```bash
python3 scripts/agentfeeds.py polling status --json
```

Install or update background polling:

```bash
python3 scripts/agentfeeds.py polling install
```

Uninstall polling only when the user no longer wants ambient refresh:

```bash
python3 scripts/agentfeeds.py polling uninstall
```

On macOS, polling uses launchd. On Linux and FreeBSD, polling uses a tagged crontab block. The runtime computes the shortest configured subscription interval and floors it at 5 minutes.

Agents should try to verify or install polling at session start. If the scheduler is unsupported or unavailable, report that Agent Feeds can still refresh explicitly but ambient refresh is degraded.

Explicit refresh remains useful for immediate freshness:

```bash
python3 scripts/agentfeeds_fetch.py --stream <subscription-id>
python3 scripts/agentfeeds_fetch.py --all
```
