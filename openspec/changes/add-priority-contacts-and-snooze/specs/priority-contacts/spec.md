# Spec: Priority Contacts

**Capability:** `priority-contacts`
**Owner:** add-priority-contacts-and-snooze
**Depends On:** trigger-detection, state-management

## Overview

Filter alerts by source using mutually exclusive whitelist or blacklist mode. Users can specify which contacts/chats should trigger alerts (whitelist) or be excluded from alerts (blacklist).

---

## ADDED Requirements

### Requirement: System MUST support filtering modes

The system MUST support three mutually exclusive filtering modes: disabled, whitelist, and blacklist.

#### Scenario: Default mode is disabled
**When** the system starts with no prior configuration
**Then** filtering mode is set to "disabled"
**And** all qualifying messages trigger alerts

#### Scenario: Whitelist mode active
**When** filtering mode is set to "whitelist"
**Then** only messages from contacts in the priority list trigger alerts
**And** messages from other sources are silently ignored

#### Scenario: Blacklist mode active
**When** filtering mode is set to "blacklist"
**Then** messages from contacts in the mute list do NOT trigger alerts
**And** messages from all other sources trigger alerts normally

#### Scenario: Mode switch preserves lists
**When** user switches from whitelist to blacklist mode (or vice versa)
**Then** a warning is shown about the mode change
**And** the opposite list is preserved but inactive

---

### Requirement: System MUST store contacts by ID

The system MUST store priority and mute lists using Telegram user/chat IDs for permanent identification.

#### Scenario: Username resolution on add
**Given** user issues `/priority add @username`
**When** the command is processed
**Then** the username is resolved to a Telegram ID via API
**And** the ID is stored in the priority list
**And** the username is stored for display purposes

#### Scenario: Username resolution failure
**Given** user issues `/priority add @nonexistent`
**When** the username cannot be resolved
**Then** an error message is sent to the user
**And** no entry is added to the list

#### Scenario: Chat ID for groups
**Given** user issues `/mute @groupname`
**When** the group is resolved
**Then** the group's chat ID is stored in the mute list

---

### Requirement: System MUST apply filter before trigger evaluation

The system MUST check priority contact filter before evaluating trigger conditions.

#### Scenario: Whitelist mode blocks non-priority message
**Given** filtering mode is "whitelist"
**And** incoming message is from a user NOT in priority list
**When** message processing begins
**Then** the message is skipped immediately
**And** trigger evaluation is NOT performed

#### Scenario: Blacklist mode blocks muted message
**Given** filtering mode is "blacklist"
**And** incoming message is from a chat in mute list
**When** message processing begins
**Then** the message is skipped immediately
**And** trigger evaluation is NOT performed

#### Scenario: Filter passes to trigger evaluation
**Given** filtering mode is "whitelist"
**And** incoming message is from a user in priority list
**When** message processing begins
**Then** the message proceeds to trigger evaluation
**And** normal DM/Mention/Reply logic applies

---

### Requirement: System MUST provide priority list commands

The system MUST respond to priority list management commands via the notification bot.

#### Scenario: Add to priority list
**Given** user sends `/priority add @username` to the bot
**When** command is processed
**Then** the contact is added to the priority list
**And** confirmation message is sent

#### Scenario: Remove from priority list
**Given** user sends `/priority remove @username` to the bot
**When** command is processed
**Then** the contact is removed from the priority list
**And** confirmation message is sent

#### Scenario: List priority contacts
**Given** user sends `/priority list` to the bot
**When** command is processed
**Then** current priority list is displayed with usernames
**And** current mode is shown

#### Scenario: Set filtering mode
**Given** user sends `/priority mode whitelist` to the bot
**When** command is processed
**Then** filtering mode is set to whitelist
**And** confirmation message includes mode explanation

#### Scenario: Disable filtering
**Given** user sends `/priority mode off` to the bot
**When** command is processed
**Then** filtering mode is set to disabled
**And** all qualifying messages trigger alerts again

---

### Requirement: System MUST provide mute list commands

The system MUST respond to mute list management commands via the notification bot.

#### Scenario: Mute a chat
**Given** user sends `/mute @chatname` to the bot
**When** command is processed
**Then** the chat is added to the mute list
**And** confirmation message is sent

#### Scenario: Unmute a chat
**Given** user sends `/unmute @chatname` to the bot
**When** command is processed
**Then** the chat is removed from the mute list
**And** confirmation message is sent

#### Scenario: List muted chats
**Given** user sends `/listmuted` to the bot
**When** command is processed
**Then** current mute list is displayed with chat names
**And** current mode is shown

---

### Requirement: System MUST persist priority state

The system MUST persist priority contacts configuration across restarts.

#### Scenario: State saved on change
**Given** user adds a contact to priority list
**When** the command completes
**Then** state is saved to state file
**And** includes mode, priority list, and mute list

#### Scenario: State loaded on startup
**Given** prior priority configuration exists in state file
**When** the system starts
**Then** filtering mode is restored
**And** priority and mute lists are restored
**And** filtering applies immediately
