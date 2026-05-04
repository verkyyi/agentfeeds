---
name: authenticated-feed-sources
description: Configure and troubleshoot AgentFeeds streams backed by authenticated APIs or private resources, including GitHub private repos, bearer-token HTTP templates, secret files, runtime catalog cache issues, and verification after subscription changes.
version: 0.1.0
author: verkyyi
license: MIT
metadata:
  hermes:
    tags: [AgentFeeds, Auth, GitHub, Private APIs, Feeds]
---

# Authenticated Feed Sources

Use this skill when AgentFeeds needs to subscribe to, refresh, or troubleshoot sources that require credentials: private GitHub repos, authenticated HTTP APIs, private dashboards, or any stream that should use a secret instead of anonymous access.

Prefer the main `agentfeeds` skill first for general operations. This skill captures the authenticated-source playbook and pitfalls that are easy to miss when a public feed template works but private data fails.

## Core Workflow

1. Identify whether the source is a template or a concrete subscription.
   - Templates define reusable source shapes.
   - Subscriptions are active configured instances.
   - Only concrete subscriptions should be verified as active streams.

2. Search and inspect the matching template:
   ```bash
   python3 scripts/agentfeeds.py templates find <query>
   python3 scripts/agentfeeds.py templates show <template-id> --json
   ```

3. Check how auth is configured.
   - Public-only templates may have `auth: none`.
   - Private HTTP APIs usually need a bearer token or service-specific auth.
   - Do not put secret values directly in YAML.

4. Store the credential as an AgentFeeds secret.
   Preferred:
   ```bash
   python3 scripts/agentfeeds.py admin secrets set <secret-name>
   ```
   For GitHub, an existing `gh` token can be reused when appropriate:
   ```bash
   gh auth token > ~/.agentfeeds/secrets/github_token.txt
   chmod 600 ~/.agentfeeds/secrets/github_token.txt
   ```

5. Patch or author the template to reference the secret, not the raw value.

6. Preview, subscribe, refresh, and read back the stream:
   ```bash
   python3 scripts/agentfeeds.py subscribe <template-id> key=value --dry-run --json
   python3 scripts/agentfeeds.py subscribe <template-id> key=value
   python3 scripts/agentfeeds.py refresh --stream <subscription-id>
   python3 scripts/agentfeeds.py streams read <subscription-id> --limit 20 --json
   python3 scripts/agentfeeds.py streams health --json
   ```

## GitHub Private Repos

GitHub returns 404 for private repo API calls when unauthenticated, even if the repo exists and `gh` is logged in. If a GitHub repo issue/PR stream works for public repos but fails for private repos, inspect the HTTP template before blaming the subscription parameters.

GitHub HTTP templates for private repo issue/PR streams should use the GitHub token service, for example:

```yaml
adapter:
  auth: bearer_token
  auth_service: github
```

The token should live in:

```text
~/.agentfeeds/secrets/github_token.txt
```

with mode 600, or be set through the AgentFeeds secret command.

## Runtime Catalog Cache Pitfall

When debugging an already-installed AgentFeeds system, editing only the bundled skill catalog may not affect runtime behavior immediately. The active runtime may read cached catalog files under:

```text
~/.agentfeeds/catalog-cache/catalog/streams/
```

If a template bug is being fixed locally for immediate verification, patch both:

```text
~/.hermes/skills/agentfeeds/catalog/streams/
~/.agentfeeds/catalog-cache/catalog/streams/
```

Then refresh the affected stream and verify with `streams read` plus `streams health`.

## JMESPath Boolean Pitfall

JMESPath boolean literals in templates must be backtick literals:

```yaml
draft: `false`
```

Bare `false` is interpreted as a field lookup and can validate as null.

## Safety Rules

- Never print tokens or secret values in the final answer.
- It is OK to state the secret path and permissions.
- Require approval before adding sources that cause side effects or expose private data externally.
- Use read-only API scopes where possible.
- Verify authenticated streams by reading the concrete subscription, not just by checking template discovery.

## References

- Session note: `references/github-private-repo-streams.md`
