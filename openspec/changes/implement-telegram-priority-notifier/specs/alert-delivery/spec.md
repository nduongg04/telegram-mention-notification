# Spec: Alert Delivery

**Capability:** `alert-delivery`
**Owner:** implement-telegram-priority-notifier
**Depends On:** trigger-detection

## Overview

Format and deliver notification messages to the user's Saved Messages with rich metadata and deep links.

---

## ADDED Requirements

### Requirement: System MUST format alerts with metadata
**Priority:** P0
**Category:** Message Formatting

The system MUST generate human-readable alerts with all required metadata.

#### Scenario: Alert for direct message
**Given** a message flagged with trigger type "DM"
**When** alert formatting occurs
**Then** the alert contains:
- Emoji indicator (🔔)
- Trigger type label ("DM")
- Chat name
- Sender name and username
- Message timestamp
- Deep link to original message
- Message preview (first 120 characters)

#### Scenario: Alert for mention
**Given** a message flagged with trigger type "Mention"
**When** alert formatting occurs
**Then** the alert contains the same fields as DM
**And** emoji indicator is 📢

#### Scenario: Alert for reply
**Given** a message flagged with trigger type "Reply"
**When** alert formatting occurs
**Then** the alert contains the same fields as DM
**And** emoji indicator is 💬

---

### Requirement: System MUST generate deep links
**Priority:** P0
**Category:** Navigation

The system MUST include clickable deep links to original messages.

#### Scenario: Private chat deep link
**Given** a message from a private chat
**When** the deep link is generated
**Then** the link format is `tg://openmessage?user_id={user_id}&message_id={msg_id}`

#### Scenario: Group/supergroup deep link
**Given** a message from a group or supergroup
**When** the deep link is generated
**Then** the link format is `tg://openmessage?chat_id={chat_id}&message_id={msg_id}`

#### Scenario: Channel deep link
**Given** a message from a channel
**When** the deep link is generated
**Then** the link format is `https://t.me/c/{channel_id}/{msg_id}`

---

### Requirement: System MUST truncate message previews
**Priority:** P1
**Category:** Message Formatting

The system MUST limit message preview length to maintain readability.

#### Scenario: Short message
**Given** a message with text shorter than 120 characters
**When** the preview is generated
**Then** the full text is included

#### Scenario: Long message
**Given** a message with text longer than 120 characters
**When** the preview is generated
**Then** the first 120 characters are included
**And** an ellipsis "..." is appended

#### Scenario: Empty or media-only message
**Given** a message without text content
**When** the preview is generated
**Then** the preview shows "[Media]" or similar placeholder

---

### Requirement: System MUST deliver to Saved Messages
**Priority:** P0
**Category:** Notification Sink

The system MUST send alerts to the user's Saved Messages chat.

#### Scenario: Successful delivery
**Given** a formatted alert message
**When** delivery is attempted
**Then** the message is sent to the "me" entity (Saved Messages)
**And** delivery succeeds

---

### Requirement: System MUST retry failed deliveries
**Priority:** P1
**Category:** Reliability

The system MUST retry transient delivery failures.

#### Scenario: Transient network error
**Given** a formatted alert ready for delivery
**When** the send attempt fails with a network error
**Then** the system retries up to 3 times
**And** uses exponential backoff between retries

#### Scenario: Permanent failure after retries
**Given** all 3 retry attempts have failed
**When** the final retry fails
**Then** the error is logged with full context
**And** processing continues (message is skipped)

---

### Requirement: System MUST rate limit alerts
**Priority:** P1
**Category:** Anti-Spam

The system MUST prevent alert flooding.

#### Scenario: Burst of qualifying messages
**Given** multiple qualifying messages arrive simultaneously
**When** alerts are being sent
**Then** alerts are rate-limited to maximum 1 per second
**And** messages are queued if necessary
