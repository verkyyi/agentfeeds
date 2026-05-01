# Unsubscribe Recipe

Use this when the user asks to remove an Agent Feeds subscription.

1. Read `~/.agentfeeds/subscriptions.yaml`.
2. Identify the subscription by stream id, state path, topic, or parameters.
3. Remove the matching subscription entry.
4. Delete only the matching generated state file after confirming the path is under `~/.agentfeeds/state/`.
5. Run `agentfeeds-fetch --regenerate-catalog`.
6. Confirm what was removed.
