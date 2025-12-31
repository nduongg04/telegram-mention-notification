# Spec: State Management

**Capability:** `state-management`
**Owner:** implement-telegram-priority-notifier
**Depends On:** trigger-detection

## Overview

Maintain persistent deduplication state to ensure each qualifying message generates exactly one alert.

---

## ADDED Requirements

### Requirement: System MUST track processed messages
**Priority:** P0
**Category:** State Management

The system MUST track processed messages to prevent duplicate alerts.

#### Scenario: First occurrence of message
**Given** a message flagged for alert
**And** the message ID is not in the processed set
**When** deduplication check occurs
**Then** the message passes the check
**And** alert delivery proceeds

#### Scenario: Duplicate message event
**Given** a message flagged for alert
**And** the message ID is already in the processed set
**When** deduplication check occurs
**Then** the message is skipped
**And** no alert is sent
**And** a log entry is created

---

### Requirement: System MUST persist state across restarts
**Priority:** P0
**Category:** Persistence

The system MUST persist deduplication state across restarts.

#### Scenario: State file write
**Given** a message is marked as processed
**When** state is persisted
**Then** the state is written to the file specified by `STATE_FILE` environment variable
**Or** defaults to `state.json` in the working directory

#### Scenario: State file read on startup
**Given** a state file exists from a previous run
**When** the system starts
**Then** the state is loaded from the file
**And** previously processed messages are not re-alerted

#### Scenario: Missing state file on startup
**Given** no state file exists (first run)
**When** the system starts
**Then** an empty state is initialized
**And** processing begins normally

---

### Requirement: System MUST write state atomically
**Priority:** P1
**Category:** Reliability

The system MUST ensure state writes are atomic to prevent corruption.

#### Scenario: State write operation
**Given** state needs to be persisted
**When** the write occurs
**Then** data is written to a temporary file first
**And** the temporary file is renamed to the target file (atomic operation)
**And** no partial or corrupted state is written

---

### Requirement: System MUST use JSON state schema
**Priority:** P0
**Category:** Data Structure

The system MUST store state in JSON format with required fields.

#### Scenario: State structure
**Given** state is being persisted
**When** JSON is serialized
**Then** the structure includes:
- `processed_messages` (object mapping "chat_id:message_id" to metadata)
- Each entry contains: `timestamp`, `trigger_type`
- `last_cleanup` timestamp

#### Scenario: State deserialization
**Given** state is loaded from file
**When** JSON is parsed
**Then** the structure is validated
**And** missing or invalid entries are skipped with a warning

---

### Requirement: System MUST clean up old state
**Priority:** P1
**Category:** Maintenance

The system MUST periodically remove old state entries to prevent unbounded growth.

#### Scenario: Cleanup trigger
**Given** the system has been running for 24 hours since last cleanup
**When** the cleanup check runs
**Then** entries older than 30 days are removed
**And** `last_cleanup` timestamp is updated

#### Scenario: State size remains bounded
**Given** continuous operation over weeks
**When** cleanup runs regularly
**Then** state file size remains under 10 MB
**And** old entries are removed successfully

---

### Requirement: System MUST use composite message keys
**Priority:** P0
**Category:** Data Integrity

The system MUST use a consistent composite key for message identification.

#### Scenario: Key generation
**Given** a message with `chat_id` and `message_id`
**When** the deduplication key is created
**Then** the format is "{chat_id}:{message_id}"
**And** the key uniquely identifies the message across all chats

---

### Requirement: System MUST recover from state corruption
**Priority:** P1
**Category:** Reliability

The system MUST handle corrupted state files gracefully.

#### Scenario: Corrupted state file
**Given** the state file contains invalid JSON
**When** the system starts
**Then** a warning is logged
**And** the corrupted file is backed up with timestamp
**And** a new empty state is initialized
**And** processing begins normally
