# Design: Priority Contacts and Snooze

## Context

The Telegram Priority Notifier currently sends alerts for all qualifying messages (DMs, mentions, replies). Users need:
1. Control over which sources can trigger alerts (priority contacts)
2. Ability to temporarily pause all alerts (snooze)

Both features require state persistence and bot command interaction.

## Goals / Non-Goals

**Goals:**
- Filter alerts by source before trigger evaluation
- Support mutually exclusive whitelist/blacklist modes
- Temporarily pause alerts with configurable behavior
- Persist state across restarts
- Handle commands via the notification bot

**Non-Goals:**
- Per-trigger-type filtering (e.g., snooze only DMs)
- Scheduled snooze (e.g., snooze every night)
- Priority levels (all priority contacts are equal)

## Decisions

### 1. Filtering Architecture

**Decision:** Add a pre-filter step in the trigger pipeline before `TriggerEngine.should_alert()`.

**Rationale:**
- Clean separation of concerns (filtering vs trigger detection)
- Filter can short-circuit early, saving API calls for chat/sender info
- Existing trigger logic remains unchanged

**Flow:**
```
Message received
    → Snooze check (if snoozed: drop or queue, exit)
    → Priority contacts check (if filtered: exit)
    → Trigger evaluation (DM/Mention/Reply)
    → Deduplication
    → Alert delivery
```

### 2. Mode Mutuality

**Decision:** Store mode as enum (`whitelist`, `blacklist`, `disabled`) with only one active at a time.

**Rationale:**
- Simpler mental model for users
- Avoids complex precedence rules
- Clear state: either filtering by inclusion, exclusion, or not filtering

**Behavior:**
- `disabled` (default): All sources allowed, no filtering
- `whitelist`: Only sources in priority list trigger alerts
- `blacklist`: All sources except muted ones trigger alerts

### 3. Contact Identification

**Decision:** Store contacts by Telegram user/chat ID (integer), not username.

**Rationale:**
- Usernames can change, IDs are permanent
- Usernames may not exist for some users
- Consistent with existing `chat_id` usage in state

**Resolution:** When user provides `@username`, resolve to ID via Telegram API and store ID.

### 4. Snooze Behavior Configuration

**Decision:** Support two modes configurable at runtime: `drop` (default) and `queue`.

**Rationale:**
- Drop mode: Simple, no resource growth, user explicitly chose to pause
- Queue mode: Important for users who want to catch up after breaks
- Runtime configurable: `/snooze --queue 2h` or config option

**Queue limits:**
- Default max: 100 alerts
- Oldest alerts dropped when limit reached (FIFO eviction)
- Queue cleared on unsnooze after delivery

### 5. State Schema Extension

**Decision:** Extend existing `state.json` with new top-level keys.

**Schema additions:**
```json
{
  "processed_messages": { ... },
  "last_cleanup": 1234567890,
  "priority_contacts": {
    "mode": "disabled",
    "whitelist": [123456789, 987654321],
    "blacklist": [111222333]
  },
  "snooze": {
    "active": false,
    "until": null,
    "behavior": "drop",
    "queue": []
  }
}
```

### 6. Command Interface

**Decision:** Use bot commands via the notification bot (not Saved Messages).

**Commands:**
| Command | Description |
|---------|-------------|
| `/priority mode <whitelist\|blacklist\|off>` | Set filtering mode |
| `/priority add @user` | Add to priority list (whitelist mode) |
| `/priority remove @user` | Remove from priority list |
| `/priority list` | Show priority list |
| `/mute @chat` | Add to mute list (blacklist mode) |
| `/unmute @chat` | Remove from mute list |
| `/listmuted` | Show muted chats |
| `/snooze <duration>` | Snooze alerts (e.g., 30m, 2h, 1d) |
| `/snooze --queue <duration>` | Snooze with queueing |
| `/unsnooze` | End snooze, deliver queue if any |
| `/snooze status` | Show snooze state |

**Rationale:**
- Bot already exists for sending alerts
- Natural interaction point for users
- Can provide immediate feedback

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Username resolution failures | Fallback to error message, require retry |
| Queue memory growth | Cap at 100, log warnings at 80% |
| Stale snooze (forgot to unsnooze) | Log in heartbeat, optional auto-unsnooze |
| Mode switch confusion | Warn when switching with existing entries |

## Migration Plan

1. New state keys added with defaults (mode=disabled, empty lists, snooze inactive)
2. Existing state files auto-upgraded on load
3. No breaking changes to existing behavior

## Open Questions

None - all questions resolved in proposal discussion.
