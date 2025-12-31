# Tasks: Add Priority Contacts and Snooze

## 1. State Schema Extension
- [x] 1.1 Extend `StateManager` with priority contacts schema (mode, whitelist, blacklist)
- [x] 1.2 Extend `StateManager` with snooze schema (active, until, behavior, queue)
- [x] 1.3 Add migration logic for existing state files (add defaults for new keys)
- [x] 1.4 Add queue management methods (add, pop, clear, size check)

## 2. Priority Contacts Filter
- [x] 2.1 Create `ContactFilter` class with mode/whitelist/blacklist logic
  - Note: Implemented as methods in `StateManager` for simplicity
- [x] 2.2 Implement `should_process()` method for pre-filter check
  - Implemented as `should_process_message()` in `StateManager`
- [x] 2.3 Add username-to-ID resolution helper using Telegram API
  - Implemented in `CommandHandler._resolve_entity()`
- [x] 2.4 Integrate filter into message handler (before trigger evaluation)

## 3. Snooze Logic
- [x] 3.1 Create `SnoozeManager` class with activation/deactivation logic
  - Note: Implemented as methods in `StateManager` for simplicity
- [x] 3.2 Implement duration parsing (30m, 2h, 1d formats)
  - Implemented as `StateManager.parse_duration()`
- [x] 3.3 Implement queue mode with FIFO eviction at limit
- [x] 3.4 Add queue delivery on unsnooze
- [x] 3.5 Integrate snooze check into message handler (before priority filter)

## 4. Bot Command Handlers
- [x] 4.1 Create `src/commands.py` with command handler framework
- [x] 4.2 Implement `/priority mode <whitelist|blacklist|off>` command
- [x] 4.3 Implement `/priority add @user` and `/priority remove @user` commands
- [x] 4.4 Implement `/priority list` command
- [x] 4.5 Implement `/mute @chat`, `/unmute @chat`, `/listmuted` commands
- [x] 4.6 Implement `/snooze <duration>` and `/snooze --queue <duration>` commands
- [x] 4.7 Implement `/unsnooze` command with queue delivery
- [x] 4.8 Implement `/snooze status` command
- [x] 4.9 Register command handlers in `main.py`

## 5. Heartbeat Integration
- [x] 5.1 Add snooze status to heartbeat log output
- [x] 5.2 Add priority filter mode to heartbeat log output

## 6. Testing
- [ ] 6.1 Test priority whitelist mode (only priority contacts trigger alerts)
- [ ] 6.2 Test priority blacklist mode (muted chats don't trigger alerts)
- [ ] 6.3 Test mode switching and state persistence
- [ ] 6.4 Test snooze activation and automatic expiration
- [ ] 6.5 Test snooze queue mode with delivery on unsnooze
- [ ] 6.6 Test queue limit and FIFO eviction
- [ ] 6.7 Test state persistence across restart with active snooze

## Dependencies
- Tasks 2.x and 3.x depend on 1.x (state schema)
- Task 4.x depends on 2.x and 3.x (filter and snooze logic)
- Task 5.x can run in parallel with 4.x
- Task 6.x depends on all implementation tasks

## Parallelizable Work
- 2.x (Priority Filter) and 3.x (Snooze) can be developed in parallel after 1.x
- 5.x (Heartbeat) can be developed in parallel with 4.x (Commands)
