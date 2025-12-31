# Design: Telegram Priority Notifier

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Telegram Priority Notifier                │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │ Config Loader│─────▶│ Auth Manager │                   │
│  │ (env vars)   │      │ (Telethon)   │                   │
│  └──────────────┘      └──────┬───────┘                   │
│                               │                            │
│                               ▼                            │
│                    ┌────────────────────┐                 │
│                    │  Message Listener  │                 │
│                    │  (event handler)   │                 │
│                    └─────────┬──────────┘                 │
│                              │                            │
│                              ▼                            │
│                    ┌────────────────────┐                 │
│                    │  Filter Engine     │                 │
│                    │  (trigger logic)   │                 │
│                    └─────────┬──────────┘                 │
│                              │                            │
│                    ┌─────────┴──────────┐                │
│                    │                    │                │
│                    ▼                    ▼                │
│          ┌──────────────────┐  ┌────────────────┐       │
│          │  State Manager   │  │ Alert Formatter│       │
│          │  (deduplication) │  │ (message build)│       │
│          └──────────────────┘  └────────┬───────┘       │
│                    │                    │                │
│                    │                    ▼                │
│                    │          ┌──────────────────┐       │
│                    │          │  Notification    │       │
│                    └─────────▶│  Sink (Saved Msg)│       │
│                               └──────────────────┘       │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Health Monitor (periodic logging)               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Config Loader
**Purpose:** Load and validate runtime configuration from environment variables

**Environment Variables:**
- `TELEGRAM_API_ID` - Telegram API ID (required)
- `TELEGRAM_API_HASH` - Telegram API Hash (required)
- `TELEGRAM_PHONE` - User phone number (required for first auth)
- `SESSION_FILE` - Path to session file (default: `telegram_session.json`)
- `STATE_FILE` - Path to deduplication state (default: `state.json`)
- `LOG_LEVEL` - Logging verbosity (default: `INFO`)

**Validation:** Fail fast on startup if required variables are missing

---

### 2. Auth Manager (Telethon Client)
**Purpose:** Establish and maintain authenticated MTProto connection

**Implementation:**
- Use `TelegramClient` from Telethon
- Session stored in local file (`SESSION_FILE`)
- First run: interactive phone code verification
- Subsequent runs: automatic session resumption
- Handle reconnection on network interruption

**Security:**
- Session file must have restricted permissions (0600)
- Never log API credentials or session data

---

### 3. Message Listener
**Purpose:** Subscribe to incoming message events

**Implementation:**
- Register event handler: `@client.on(events.NewMessage(incoming=True))`
- Normalize message metadata (chat_id, message_id, sender, text, entities, reply_to)
- Pass normalized data to Filter Engine
- Handle all message types: private, group, supergroup, channel

**Error Handling:**
- Log and skip malformed messages
- Continue processing on handler exceptions

---

### 4. Filter Engine
**Purpose:** Apply trigger conditions deterministically

**Trigger Logic:**
```python
def should_alert(message, user_id):
    # Exclusion: message from self
    if message.sender_id == user_id:
        return False, None

    # Exclusion: service messages
    if message.is_service:
        return False, None

    # Trigger A: Direct Message
    if message.is_private:
        return True, "DM"

    # Trigger B: Mention
    if is_mentioned(message, user_id):
        return True, "Mention"

    # Trigger C: Reply to user's message
    if is_reply_to_user(message, user_id):
        return True, "Reply"

    return False, None
```

**Mention Detection:**
- Check for `@username` in text
- Check for `MessageEntityMention` or `MessageEntityMentionName` entities matching user ID

**Reply Detection:**
- Check `reply_to_msg_id`
- Fetch replied message
- Compare `replied_message.sender_id == user_id`

---

### 5. State Manager
**Purpose:** Prevent duplicate alerts

**State Structure (JSON):**
```json
{
  "processed_messages": {
    "chat_id:message_id": {
      "timestamp": 1704067200,
      "trigger_type": "DM"
    }
  },
  "last_cleanup": 1704067200
}
```

**Operations:**
- `is_processed(chat_id, message_id)` - Check if message already alerted
- `mark_processed(chat_id, message_id, trigger_type)` - Record alert sent
- `cleanup_old_entries()` - Remove entries older than 30 days (periodic)

**Persistence:**
- Write to `STATE_FILE` after each alert
- Atomic write (write to temp file, then rename)
- Load on startup (create empty if missing)

---

### 6. Alert Formatter
**Purpose:** Build human-readable alert messages

**Format:**
```
🔔 [TRIGGER_TYPE]
Chat: {chat_name}
From: {sender_name} (@{username})
Time: {timestamp}
Link: {deep_link}

Preview:
{first_120_chars}
```

**Deep Link Generation:**
- Private chats: `tg://openmessage?user_id={user_id}&message_id={msg_id}`
- Groups/Supergroups: `tg://openmessage?chat_id={chat_id}&message_id={msg_id}`
- Channels: `https://t.me/c/{channel_id}/{msg_id}`

**Emoji Mapping:**
- DM: 🔔
- Mention: 📢
- Reply: 💬

---

### 7. Notification Sink
**Purpose:** Send alerts to Saved Messages

**Implementation:**
- Get "Saved Messages" chat: `client.get_entity("me")`
- Send formatted message: `client.send_message("me", formatted_alert)`
- Retry on transient failures (network errors)
- Rate limit: max 1 alert per second (anti-spam)

---

### 8. Health Monitor
**Purpose:** Periodic logging for operational visibility

**Behavior:**
- Log startup message with version and config summary
- Every 1 hour: log heartbeat with uptime and message count
- On reconnection: log disconnect/reconnect events
- On error: log error details with context

**Metrics Tracked:**
- Total messages received
- Alerts sent (by trigger type)
- Deduplication hits
- Connection uptime

---

## Data Flow

1. **Startup:**
   - Load config from environment
   - Initialize Telethon client with session file
   - Load deduplication state from JSON
   - Start message listener
   - Log health status

2. **Message Received:**
   - Listener receives `NewMessage` event
   - Normalize message metadata
   - Filter Engine evaluates triggers → (should_alert, trigger_type)
   - If `should_alert == False`: discard
   - State Manager checks deduplication → already processed?
   - If duplicate: log and skip
   - Alert Formatter builds message
   - Notification Sink sends to Saved Messages
   - State Manager marks processed and persists state

3. **Reconnection:**
   - Telethon auto-reconnects on network failure
   - Health Monitor logs reconnection event
   - Resume message listening

---

## Technology Choices

### Why Telethon?
- Pure Python, stable, well-documented
- MTProto user client (not Bot API)
- Built-in session management
- Event-driven architecture
- Active maintenance

### Why JSON for State?
- Simple, human-readable
- No external dependencies
- Adequate for single-user, single-process use case
- Easy backup and debugging

### Alternative Considered: SQLite
- Rejected for v1: adds complexity without clear benefit
- Future: migrate if state grows large (>10k entries)

---

## Error Handling Strategy

| Error Type | Handling |
|------------|----------|
| Missing env vars | Fail fast on startup with clear error |
| Auth failure | Exit with instructions to check credentials |
| Network disconnect | Auto-reconnect (Telethon built-in) |
| Message parsing error | Log error, skip message, continue |
| State write failure | Log error, continue (alert still sent) |
| Rate limit (Telegram) | Exponential backoff, log warning |
| Saved Messages send failure | Retry 3 times, then log and skip |

---

## Security Considerations

1. **Session Storage:**
   - File permissions: 0600 (owner read/write only)
   - Never commit session file to version control

2. **Environment Variables:**
   - Load via `.env` file (gitignored)
   - No hardcoded credentials in source code

3. **Read-Only Access:**
   - No message deletion or modification
   - No outbound messages except to Saved Messages

4. **Logging:**
   - Never log message content verbatim (privacy)
   - Only log metadata (chat ID, message ID, trigger type)

---

## Deployment Considerations

### Local Development
- Python virtual environment (`venv`)
- Manual startup: `python main.py`
- Logs to stdout/stderr

### Future Production (Out of Scope for Proposal)
- Process manager: systemd, PM2, or Docker
- Log aggregation: file-based or syslog
- Monitoring: health check endpoint or log scraping

---

## Open Questions (Deferred)

1. Should certain channels be filtered differently?
   - **Decision:** v1 treats channels like any other chat (alerts on mentions/replies)

2. Should alerts be grouped or throttled?
   - **Decision:** v1 sends one alert per qualifying message immediately

3. Should there be chat-level whitelist/blacklist?
   - **Decision:** Out of scope for v1

---

## Testing Strategy

### Unit Tests
- Filter Engine logic (trigger conditions)
- Alert Formatter (message formatting)
- State Manager (deduplication)

### Integration Tests
- Message listener with mock Telethon events
- End-to-end flow with test messages

### Manual Tests
- Send DM → verify alert
- Mention in group → verify alert
- Reply to own message → verify alert
- Self-message → verify no alert
- Duplicate message → verify single alert
- 7-day continuous run test

---

## Success Metrics

- **Reliability:** 0 crashes over 7-day test period
- **Latency:** p95 alert delivery < 5 seconds
- **Accuracy:** 0 false negatives, 0 duplicate alerts
- **Deduplication:** 100% effective (no duplicates on replay)
