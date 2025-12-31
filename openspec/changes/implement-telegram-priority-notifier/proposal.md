# Proposal: Implement Telegram Priority Notifier

**Change ID:** `implement-telegram-priority-notifier`
**Status:** Proposed
**Created:** 2025-12-31

## Overview

Implement a long-running Python service that monitors all incoming Telegram messages on a user account and sends priority alerts to Saved Messages for messages matching specific trigger conditions (direct messages, mentions, and replies to user's messages).

## Why

Telegram's native notification system does not support mentions-only behavior, consistent alerting for replies in muted chats, or centralized direct message escalation, causing users to miss high-priority messages.

## Problem Statement

Telegram's native notification system does not support:
- Global "mentions-only" behavior across all chats
- Consistent alerting for replies in muted conversations
- Centralized escalation of all direct messages
- Conditional logic across different chat types

As a result, high-priority messages are frequently missed when users mute chats to reduce notification noise.

## Proposed Solution

Build a Python-based notification service using Telethon (MTProto client) that:

1. Authenticates as the user's Telegram account
2. Listens to all incoming messages in real-time
3. Applies deterministic trigger logic (DM, mention, or reply)
4. Sends formatted alerts to the user's Saved Messages
5. Maintains deduplication state to prevent duplicate alerts
6. Runs continuously with automatic reconnection on network failures

## Success Criteria

- ✅ 100% of qualifying messages generate exactly one alert
- ✅ Alerts delivered within ≤5 seconds (best-effort)
- ✅ System runs for 7+ days without manual intervention
- ✅ No duplicate alerts generated
- ✅ Works correctly with all chats muted

## Scope

### In Scope
- Message monitoring (private chats, groups, supergroups, channels)
- Trigger detection (DM, mention, reply)
- Alert formatting and delivery to Saved Messages
- JSON-based deduplication state
- Environment-based configuration
- Health check logging
- Automatic reconnection

### Out of Scope (v1)
- Keyword-based triggers
- User-configurable UI
- Multi-user support
- External alert channels (email, Slack, etc.)
- Historical message backfill
- Whitelist/blacklist filtering
- Alert grouping or throttling

## Capabilities Delivered

This change introduces the following new capabilities:

1. **telegram-authentication** - User account authentication via MTProto
2. **message-monitoring** - Real-time message event subscription
3. **trigger-detection** - Rule-based message filtering
4. **alert-delivery** - Formatted notification dispatch
5. **state-management** - Deduplication and persistence
6. **system-reliability** - Health monitoring and reconnection

## Dependencies

- Python 3.8+
- Telethon library
- Telegram API credentials (API ID, API Hash)
- Phone number for authentication

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Excessive alert volume | Strict trigger logic with clear exclusions |
| Missed messages on disconnect | Automatic reconnection + health logging |
| Account rate limits | Conservative API usage, no bulk operations |
| Silent failures | Periodic health check logging |
| Session credential leakage | Environment variables only, no hardcoding |

## Related Changes

None (initial implementation)
