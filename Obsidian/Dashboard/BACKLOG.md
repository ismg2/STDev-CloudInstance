# Backlog Dashboard

## Requirements table (Dataview)
```dataview
TABLE id, state, priority, target_version, owner, tests_updated, pr_opened
FROM "Obsidian/Requirements"
WHERE id != null
SORT target_version ASC, priority ASC, id ASC
```

## Requirements by state (Dataview)
```dataview
TABLE id, title, target_version
FROM "Obsidian/Requirements"
WHERE state = "Selected"
SORT id ASC
```

## Open TODO tasks (Tasks plugin)
```tasks
not done
path includes Obsidian/Requirements
sort by path
```
