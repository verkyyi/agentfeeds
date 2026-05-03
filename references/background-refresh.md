# Background Refresh

Most agent flows should refresh explicitly:

```bash
python scripts/agentfeeds_fetch.py --stream <subscription-id>
python scripts/agentfeeds_fetch.py --all
```

Install background polling only when the user asks for subscriptions to stay warm between conversations:

```bash
python scripts/polling/install.py
```

Uninstall polling:

```bash
python scripts/polling/uninstall.py
```

On macOS, polling uses launchd. On Linux and FreeBSD, polling uses a tagged crontab block. The runtime computes the shortest configured subscription interval and floors it at 5 minutes.

Do not install or uninstall polling without explicit user intent because it changes host scheduler state.
