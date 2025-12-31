1. Objective

Provide reliable, low-noise notifications for high-priority Telegram messages that would otherwise be missed due to muted chats or notification overload.

The system listens to all incoming Telegram messages on the user’s account and generates explicit alert messages when predefined priority conditions are met.

2. Problem Statement

Telegram’s native notification controls do not support:

Global “mentions-only” behavior across chats

Consistent alerting for replies to muted conversations

Centralized escalation of all direct messages

Conditional logic across heterogeneous chat types

As a result, important messages are frequently missed.

3. Success Criteria

The product is successful if:

The user receives an alert for 100% of qualifying messages

Alerts are delivered within ≤5 seconds of message receipt (best-effort)

Alert volume is low enough that no alerts are ignored

No duplicate alerts are generated

The system runs unattended for weeks without intervention

4. In-Scope Functionality
4.1 Message Sources

The system must monitor:

Private chats (direct messages)

Group chats

Supergroups

Channels (read-only)

All message types are treated as inbound events.

4.2 Trigger Conditions

An alert MUST be generated if any of the following conditions are true:

A. Direct Messages

Message is from a private chat

Sender is not the user

B. Mentions

Message contains a textual @username mention

Message contains a Telegram entity referencing the user ID

C. Replies

Message is a reply to a message authored by the user

4.3 Exclusions (Non-Triggers)

Alerts MUST NOT be generated when:

Message is authored by the user

Message is a service/system message

Message fails to meet any trigger condition

(Additional exclusions may be added later but are out of scope for v1.)

5. Notification Delivery
5.1 Destination

Alerts must be delivered to:

Telegram Saved Messages of the same user account

No external services, bots, or secondary accounts are required.

5.2 Alert Format

Each alert must include:

Trigger Type: DM, Mention, or Reply

Chat Name

Sender Name / Username

Message Timestamp

Message Deep Link

Message Preview (first ~120 characters)

Alerts must be concise and human-readable.

6. Non-Functional Requirements
6.1 Reliability

Best-effort delivery

Automatic reconnection on network failure

No manual restarts under normal conditions

6.2 Deduplication

Each source message may generate at most one alert

Message ID–based deduplication is required

6.3 Performance

Must handle idle and burst message loads gracefully

CPU and memory usage are non-critical but must be stable

7. Architecture Overview
7.1 Core Components

Telegram User Account Client

Authenticated via MTProto

Persistent session storage

Message Listener

Subscribes to incoming message events

Normalizes message metadata

Filter Engine

Applies trigger conditions deterministically

Emits alert events

Notification Sink

Formats alerts

Sends messages to Saved Messages

State Store

Tracks processed message IDs

Prevents duplicate alerts

8. Technology Constraints

Must use Telegram MTProto (not Bot API)

Must authenticate as a user account

Must run as a long-lived process

Language and framework are implementation details and not mandated.

9. Security Considerations

Session credentials must not be hardcoded

Secrets must be stored securely (environment variables or encrypted storage)

Read-only access: no message modification or deletion

10. Out of Scope (v1)

Keyword-based triggers

User-configurable UI

Multi-user support

External alert channels (email, Slack, etc.)

Historical backfill of messages

11. Risks & Mitigations
Risk	Mitigation
Excessive alert volume	Strict trigger logic
Missed messages due to disconnect	Reconnect + logging
Account rate limits	Conservative API usage
Silent failures	Periodic health logging
12. Open Questions (Explicitly Deferred)

Should channels be filtered differently?

Should certain chats be whitelisted/blacklisted?

Should alerts be grouped or throttled?

These are intentionally excluded from v1.

13. Acceptance Criteria

The system is accepted when:

Muting all Telegram chats still allows all qualifying alerts through

A mention or reply reliably generates a Saved Messages alert

Every DM generates exactly one alert

The system runs continuously for 7 days without manual intervention