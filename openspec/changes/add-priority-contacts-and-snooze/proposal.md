# Proposal: Add Priority Contacts and Snooze

**Change ID:** `add-priority-contacts-and-snooze`
**Status:** Proposed
**Created:** 2025-12-31

## Overview

Extend the Telegram Priority Notifier with two features: Priority Contacts (whitelist/blacklist mode for filtering alerts by source) and Snooze (temporarily pause all alerts).

## Why

Users need finer control over which messages trigger alerts and the ability to temporarily silence notifications without stopping the service. Currently, all qualifying messages (DMs, mentions, replies) generate alerts regardless of source, and there's no way to pause alerts temporarily.

## What Changes

- **Priority Contacts**: Filter alerts by source using mutually exclusive whitelist or blacklist mode
  - Whitelist mode: only get alerts from specified people/groups
  - Blacklist mode: exclude specified noisy chats from alerts
  - Commands: `/priority add @user`, `/mute @group`, `/unmute @group`, `/listmuted`, `/listpriority`, `/priority mode whitelist|blacklist`
- **Snooze**: Temporarily pause all alerts for a configurable duration
  - Commands: `/snooze 30m`, `/snooze 2h`, `/unsnooze`, `/snooze status`
  - Configurable behavior: drop silently (default) or queue and deliver on unsnooze

## Impact

- **Affected specs**:
  - `trigger-detection` (MODIFIED - add contact filter check before trigger evaluation)
  - New: `priority-contacts` (source-based filtering)
  - New: `snooze` (temporary alert pause)
- **Affected code**:
  - `src/triggers.py` - Add pre-filter for priority contacts and snooze state
  - `src/state.py` - Add storage for priority list, mute list, snooze state, and optional alert queue
  - `main.py` - Register bot command handlers
  - New: `src/commands.py` - Bot command handlers for /priority, /mute, /snooze

## Success Criteria

- Priority contacts filter correctly applied before trigger evaluation
- Whitelist and blacklist modes are mutually exclusive
- Snooze pauses all alerts for the specified duration
- Commands work via the notification bot
- State persists across restarts
- Clear user feedback for all commands

## Capabilities Delivered

1. **priority-contacts** - Source-based alert filtering (whitelist/blacklist)
2. **snooze** - Temporary alert pause with configurable behavior

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| User confusion between modes | Clear feedback on mode switch, warn when changing modes |
| Forgetting snooze is active | Log snooze status in heartbeat, optional reminder at snooze end |
| Queue growing too large | Cap queue size (default 100), warn when approaching limit |
| Invalid duration parsing | Validate duration format, provide clear error messages |

## Related Changes

- Extends: `implement-telegram-priority-notifier`
