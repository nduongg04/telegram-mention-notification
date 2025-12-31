# Spec: Snooze

**Capability:** `snooze`
**Owner:** add-priority-contacts-and-snooze
**Depends On:** state-management

## Overview

Temporarily pause all alerts for a configurable duration. Supports two behaviors: drop alerts silently (default) or queue them for delivery when snooze ends.

---

## ADDED Requirements

### Requirement: System MUST support snooze activation

The system MUST allow users to activate snooze for a specified duration.

#### Scenario: Activate snooze with duration
**Given** user sends `/snooze 30m` to the bot
**When** command is processed
**Then** snooze is activated
**And** snooze end time is set to current time + 30 minutes
**And** confirmation message shows end time

#### Scenario: Snooze with hours
**Given** user sends `/snooze 2h` to the bot
**When** command is processed
**Then** snooze is activated for 2 hours
**And** confirmation message shows end time

#### Scenario: Snooze with days
**Given** user sends `/snooze 1d` to the bot
**When** command is processed
**Then** snooze is activated for 1 day (24 hours)
**And** confirmation message shows end time

#### Scenario: Invalid duration format
**Given** user sends `/snooze abc` to the bot
**When** command is processed
**Then** an error message is sent
**And** valid formats are explained (e.g., 30m, 2h, 1d)
**And** snooze is NOT activated

#### Scenario: Extend existing snooze
**Given** snooze is already active
**And** user sends `/snooze 1h` to the bot
**When** command is processed
**Then** snooze end time is updated to current time + 1 hour
**And** confirmation shows new end time

---

### Requirement: System MUST support snooze deactivation

The system MUST allow users to manually end snooze early.

#### Scenario: Manual unsnooze
**Given** snooze is active
**And** user sends `/unsnooze` to the bot
**When** command is processed
**Then** snooze is deactivated immediately
**And** confirmation message is sent

#### Scenario: Unsnooze when not snoozed
**Given** snooze is NOT active
**And** user sends `/unsnooze` to the bot
**When** command is processed
**Then** a message indicates snooze was not active

#### Scenario: Automatic snooze expiration
**Given** snooze is active
**And** current time exceeds snooze end time
**When** a new message is received
**Then** snooze is automatically deactivated
**And** normal alert processing resumes

---

### Requirement: System MUST support snooze status check

The system MUST allow users to check current snooze status.

#### Scenario: Check status when snoozed
**Given** snooze is active until 3:00 PM
**And** user sends `/snooze status` to the bot
**When** command is processed
**Then** message shows snooze is active
**And** shows remaining time
**And** shows configured behavior (drop or queue)

#### Scenario: Check status when not snoozed
**Given** snooze is NOT active
**And** user sends `/snooze status` to the bot
**When** command is processed
**Then** message shows snooze is not active

---

### Requirement: System MUST support configurable snooze behavior

The system MUST support two snooze behaviors: drop (default) and queue.

#### Scenario: Drop mode (default)
**Given** snooze is active with behavior "drop"
**When** a qualifying message is received
**Then** the message is not queued
**And** no alert is sent
**And** the message is logged as skipped due to snooze

#### Scenario: Queue mode activation
**Given** user sends `/snooze --queue 2h` to the bot
**When** command is processed
**Then** snooze is activated with behavior "queue"
**And** confirmation shows queue mode is active

#### Scenario: Queue mode stores alerts
**Given** snooze is active with behavior "queue"
**When** a qualifying message is received
**Then** the formatted alert is added to the queue
**And** the message is logged as queued

#### Scenario: Queue delivery on unsnooze
**Given** snooze is active with queued alerts
**And** user sends `/unsnooze` to the bot
**When** command is processed
**Then** all queued alerts are delivered
**And** queue is cleared
**And** summary of delivered alerts is shown

---

### Requirement: System MUST limit queue size

The system MUST limit queue size to prevent unbounded memory growth.

#### Scenario: Queue limit reached
**Given** snooze is active with queue behavior
**And** queue contains 100 alerts (default max)
**When** a new qualifying message is received
**Then** the oldest alert is removed (FIFO eviction)
**And** the new alert is added to the queue
**And** a warning is logged

#### Scenario: Queue approaching limit warning
**Given** snooze is active with queue behavior
**And** queue size reaches 80% of limit
**When** a new alert is queued
**Then** a warning message is sent to the user
**And** queue size and limit are shown

---

### Requirement: System MUST block alerts during snooze

The system MUST check snooze state before any message processing.

#### Scenario: Message blocked by snooze
**Given** snooze is active
**When** any message is received
**Then** snooze check occurs first (before priority filter)
**And** if snoozed, message is dropped or queued
**And** no further processing occurs

#### Scenario: Snooze check passes
**Given** snooze is NOT active
**When** a message is received
**Then** message proceeds to priority contact filter
**And** normal processing continues

---

### Requirement: System MUST persist snooze state

The system MUST persist snooze configuration across restarts.

#### Scenario: Snooze state saved
**Given** snooze is activated
**When** state is persisted
**Then** snooze active status is saved
**And** snooze end time is saved
**And** snooze behavior is saved
**And** queue is saved (if queue mode)

#### Scenario: Snooze state restored on startup
**Given** snooze was active before shutdown
**And** snooze end time has NOT passed
**When** the system starts
**Then** snooze is restored as active
**And** snooze end time is restored
**And** queue is restored (if any)

#### Scenario: Expired snooze on startup
**Given** snooze was active before shutdown
**And** snooze end time HAS passed
**When** the system starts
**Then** snooze is marked inactive
**And** queued alerts are delivered (if any)
**And** startup log notes snooze expired

---

### Requirement: System MUST log snooze status in heartbeat

The system MUST include snooze status in periodic heartbeat logs.

#### Scenario: Heartbeat with active snooze
**Given** snooze is active
**When** heartbeat is logged
**Then** snooze status is included
**And** remaining time is shown
**And** queue size is shown (if queue mode)

#### Scenario: Heartbeat without snooze
**Given** snooze is NOT active
**When** heartbeat is logged
**Then** snooze is shown as inactive
