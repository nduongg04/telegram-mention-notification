# Spec: Message Monitoring

**Capability:** `message-monitoring`
**Owner:** implement-telegram-priority-notifier
**Depends On:** telegram-authentication

## Overview

Subscribe to and process all incoming Telegram message events in real-time across all chat types.

---

## ADDED Requirements

### Requirement: System MUST subscribe to all messages
**Priority:** P0
**Category:** Event Handling

The system MUST listen to all incoming messages across all chat types.

#### Scenario: Private chat message received
**Given** an authenticated Telegram connection
**When** a message is received in a private chat
**Then** the message event is captured
**And** forwarded to the filter engine

#### Scenario: Group message received
**Given** an authenticated Telegram connection
**When** a message is received in a group or supergroup
**Then** the message event is captured
**And** forwarded to the filter engine

#### Scenario: Channel message received
**Given** an authenticated Telegram connection
**When** a message is received in a subscribed channel
**Then** the message event is captured
**And** forwarded to the filter engine

---

### Requirement: System MUST normalize message metadata
**Priority:** P0
**Category:** Data Processing

The system MUST extract and normalize key message metadata for downstream processing.

#### Scenario: Message with all metadata
**Given** a new message event
**When** the message is processed
**Then** the following fields are extracted:
- `chat_id`
- `message_id`
- `sender_id`
- `sender_name`
- `sender_username`
- `text` (if present)
- `entities` (mentions, etc.)
- `reply_to_msg_id` (if present)
- `timestamp`
- `is_private` (boolean)
- `is_service` (boolean)

#### Scenario: Message without optional fields
**Given** a message without username or text
**When** the message is processed
**Then** missing fields are set to `None` or empty string
**And** processing continues normally

---

### Requirement: System MUST filter incoming messages only
**Priority:** P0
**Category:** Event Filtering

The system MUST only process incoming messages, not outgoing messages.

#### Scenario: Incoming message
**Given** a message event with `incoming=True`
**When** the event is received
**Then** the message is processed

#### Scenario: Outgoing message
**Given** a message event with `incoming=False`
**When** the event is received
**Then** the message is ignored
**And** no processing occurs

---

### Requirement: System MUST handle errors gracefully
**Priority:** P1
**Category:** Reliability

The system MUST continue processing messages even if individual messages fail to parse.

#### Scenario: Malformed message
**Given** a message event that raises a parsing exception
**When** the exception occurs
**Then** the error is logged with message metadata
**And** the message is skipped
**And** the listener continues processing subsequent messages

#### Scenario: Unknown message type
**Given** a message with an unexpected structure
**When** metadata extraction fails
**Then** the error is logged
**And** the message is skipped
**And** processing continues

---

### Requirement: System MUST NOT modify messages
**Priority:** P0
**Category:** Security

The system MUST operate in read-only mode and never modify or delete messages.

#### Scenario: Message processing
**Given** any message event
**When** the message is processed
**Then** no API calls are made to modify or delete the message
**And** the message remains unchanged in the chat
