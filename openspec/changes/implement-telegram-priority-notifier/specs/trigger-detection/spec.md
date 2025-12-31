# Spec: Trigger Detection

**Capability:** `trigger-detection`
**Owner:** implement-telegram-priority-notifier
**Depends On:** message-monitoring

## Overview

Apply deterministic rules to classify messages as alert-worthy based on three trigger conditions: direct messages, mentions, and replies to user's messages.

---

## ADDED Requirements

### Requirement: System MUST alert on direct messages
**Priority:** P0
**Category:** Trigger Logic

The system MUST generate alerts for all non-self direct messages.

#### Scenario: Incoming private message from another user
**Given** a message from a private chat
**And** the sender is not the authenticated user
**When** trigger evaluation occurs
**Then** the message is flagged for alert
**And** trigger type is set to "DM"

#### Scenario: Private message from self (Saved Messages)
**Given** a message from a private chat
**And** the sender is the authenticated user
**When** trigger evaluation occurs
**Then** the message is NOT flagged for alert

---

### Requirement: System MUST alert on mentions
**Priority:** P0
**Category:** Trigger Logic

The system MUST generate alerts when the user is mentioned via @username or entity.

#### Scenario: Textual @username mention
**Given** a message containing "@{user_username}" in text
**And** the username matches the authenticated user
**When** trigger evaluation occurs
**Then** the message is flagged for alert
**And** trigger type is set to "Mention"

#### Scenario: Entity-based mention
**Given** a message with a `MessageEntityMention` or `MessageEntityMentionName` entity
**And** the entity references the authenticated user's ID
**When** trigger evaluation occurs
**Then** the message is flagged for alert
**And** trigger type is set to "Mention"

#### Scenario: Message without mention
**Given** a message in a group
**And** the message does not contain the user's username or mention entity
**When** trigger evaluation occurs
**Then** the message is NOT flagged for alert
**And** evaluation continues to check reply condition

---

### Requirement: System MUST alert on replies to user
**Priority:** P0
**Category:** Trigger Logic

The system MUST generate alerts when a message is a reply to the user's own message.

#### Scenario: Reply to user's message
**Given** a message with `reply_to_msg_id` set
**And** the replied-to message was sent by the authenticated user
**When** trigger evaluation occurs
**Then** the message is flagged for alert
**And** trigger type is set to "Reply"

#### Scenario: Reply to another user's message
**Given** a message with `reply_to_msg_id` set
**And** the replied-to message was NOT sent by the authenticated user
**When** trigger evaluation occurs
**Then** the message is NOT flagged for alert

#### Scenario: No reply
**Given** a message without `reply_to_msg_id`
**When** trigger evaluation occurs
**Then** reply condition is not satisfied
**And** no alert is generated (unless other triggers apply)

---

### Requirement: System MUST NOT alert on service messages
**Priority:** P0
**Category:** Trigger Logic

The system MUST NOT generate alerts for service or system messages.

#### Scenario: Service message (e.g., user joined group)
**Given** a message with `is_service=True`
**When** trigger evaluation occurs
**Then** the message is NOT flagged for alert
**And** processing stops immediately

---

### Requirement: System MUST NOT alert on self messages
**Priority:** P0
**Category:** Trigger Logic

The system MUST NOT generate alerts for messages sent by the user.

#### Scenario: Message from self in group
**Given** a message in a group chat
**And** the sender is the authenticated user
**When** trigger evaluation occurs
**Then** the message is NOT flagged for alert
**And** processing stops immediately

---

### Requirement: System MUST use single trigger per message
**Priority:** P1
**Category:** Alert Generation

The system MUST classify each message with at most one trigger type, prioritizing DM > Mention > Reply.

#### Scenario: Message matching multiple triggers
**Given** a direct message that also mentions the user
**When** trigger evaluation occurs
**Then** trigger type is set to "DM"
**And** mention trigger is not reported

#### Scenario: Group message with mention and reply
**Given** a group message that both mentions the user and replies to user's message
**When** trigger evaluation occurs
**Then** trigger type is set to "Mention"
**And** reply trigger is not reported
