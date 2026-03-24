# Plugin Setup for Option B

## Install plugins
In Obsidian:
1. Open Settings.
2. Community plugins -> Turn off Safe mode.
3. Browse and install core plugins:
- Dataview
- Tasks
- Templater

Optional plugins (add only if needed):
- QuickAdd
- Kanban

## Configure Templater
1. Settings -> Templater.
2. Template folder location: Obsidian/03-Templates
3. Enable "Trigger Templater on new file creation".

## Configure QuickAdd (optional)
Create one macro:
- New Requirement: create note in Obsidian/01-Requirements from REQUIREMENT_TEMPLATE.md

## Dataview sanity check
Open [BACKLOG.md](BACKLOG.md). If tables render, Dataview is active.

## Tasks sanity check
Create one test task in any requirement note:
- [ ] TODO-REQ-999-DISCUSS
Then verify it appears in [BACKLOG.md](BACKLOG.md).
