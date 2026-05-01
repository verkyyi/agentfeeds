# Discover Recipe

Use this when the user asks what Agent Feeds streams are available.

1. Ensure `~/.agentfeeds/catalog-cache/INDEX.json` exists.
2. If missing, run `agentfeeds-fetch --update-catalog`.
3. Search the index by topic, tag, stream type, and description.
4. Present the best matches with:
   - title
   - stream id
   - required parameters
   - auth requirement
   - quality tier
5. Suggest one best stream to subscribe to when there is a clear match.
