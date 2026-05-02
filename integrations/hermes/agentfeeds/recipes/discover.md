# Discover Recipe

Use this when the user asks what Agent Feeds streams are available.

1. Run `agentfeeds discover <query>`.
2. Present the best matches with:
   - title
   - provider id
   - required parameters
   - auth requirement
   - quality tier
3. Suggest one best stream to subscribe to when there is a clear match.
4. If no provider fits, offer to draft one with `recipes/provider-authoring.md`.
