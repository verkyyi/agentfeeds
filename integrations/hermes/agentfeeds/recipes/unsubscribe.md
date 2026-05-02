# Unsubscribe Recipe

Use this when the user asks to remove an Agent Feeds subscription.

1. Identify the subscription by stream id, state path, topic, or parameters.
2. Run `agentfeeds unsubscribe <stream-id> key=value ...`.
3. If multiple subscriptions match the same id, include distinguishing parameters or use `--all-matching` only when the user clearly wants every matching subscription removed.
4. Confirm what was removed.
