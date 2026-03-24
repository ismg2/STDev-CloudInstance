# Backlog Dashboard

## Requirements table (Dataview)
```dataview
TABLE id, state, priority, target_version, owner, tests_updated, pr_opened
FROM "Obsidian/01-Requirements"
WHERE id != null
SORT target_version ASC, priority ASC, id ASC
```

## Requirements by state (Dataview)
```dataview
TABLE id, title, target_version
FROM "Obsidian/01-Requirements"
WHERE state = "Selected"
SORT id ASC
```

## Open TODO tasks (Tasks plugin)
```tasks
not done
path includes Obsidian/01-Requirements
sort by path
```
