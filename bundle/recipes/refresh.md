# Refresh Recipe

Use this when the user asks to refresh Agent Feeds data.

For one stream:

```bash
agentfeeds refresh <subscription-id>
```

For every stream:

```bash
agentfeeds refresh --all
```

After refresh, read the relevant state file again before answering.
