# Template Authoring

Use local templates when no built-in template fits a private file, dashboard, API, or approved read-only command.

Built-in templates are sourced from the standalone catalog repository:

```text
https://github.com/verkyyi/agentfeeds-catalog
```

They are cached under `~/.agentfeeds/catalog-cache/` by `python3 scripts/agentfeeds_fetch.py --update-catalog`. User-local templates live under `~/.agentfeeds/templates/` and are merged into discovery at runtime.

Start by checking built-ins:

```bash
python3 scripts/agentfeeds.py templates search <topic>
python3 scripts/agentfeeds.py templates show <template-id>
```

List supported adapter kinds:

```bash
python3 scripts/agentfeeds.py templates adapters
```

Scaffold a draft:

```bash
python3 scripts/agentfeeds.py templates scaffold <adapter-kind> <template-id>
```

The scaffold command prints the generated file paths. Edit the template YAML, then validate and dry-run it:

```bash
python3 scripts/agentfeeds.py templates validate
python3 scripts/agentfeeds.py templates test <template-id> key=value
```

Local templates live under the Agent Feeds runtime root:

```text
~/.agentfeeds/templates/streams/
~/.agentfeeds/templates/schemas/event-types/
```

Use `local_command` only for explicitly approved read-only commands. Commands must be argv arrays, not shell strings. Avoid commands that mutate files, cloud resources, accounts, or external services.
