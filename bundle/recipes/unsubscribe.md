# Unsubscribe Recipe

Use this when the user asks to remove an Agent Feeds subscription.

1. Identify the concrete subscription id by listing `agentfeeds list` or reading `~/.agentfeeds/catalog.md`.
2. Run `agentfeeds unsubscribe <subscription-id>`.
3. If the user names a provider/template instead, show matching concrete subscriptions and ask which one to remove.
4. Confirm what was removed.
