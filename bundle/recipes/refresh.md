# Refresh Recipe

Use this when the user asks to refresh Agent Feeds data.

For one stream:

```bash
agentfeeds-fetch --stream <stream-id>
```

For every stream:

```bash
agentfeeds-fetch --all
```

After refresh, read the relevant state file again before answering.
