# Tasks: Implement Telegram Priority Notifier

**Change ID:** `implement-telegram-priority-notifier`

## Overview
Implementation tasks for the Telegram priority notification system, ordered to deliver user-visible progress incrementally.

---

## Task List

### Phase 1: Foundation & Authentication (Days 1-2)

#### 1. Setup project structure and dependencies
- [x] Create Python virtual environment
- [x] Create `requirements.txt` with dependencies: `telethon`, `python-dotenv`
- [x] Create `.env.example` template with required variables
- [x] Create `.gitignore` (exclude `.env`, `*.session`, `state.json`)
- [x] Initialize basic project structure: `src/`, `tests/`, `main.py`

**Validation:** `pip install -r requirements.txt` succeeds ✅

---

#### 2. Implement configuration loader
- [x] Create `src/config.py`
- [x] Load environment variables via `python-dotenv`
- [x] Validate required variables: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`
- [x] Support optional variables: `SESSION_FILE`, `STATE_FILE`, `LOG_LEVEL`
- [x] Fail fast with clear error on missing required vars

**Validation:** Running with missing env vars shows clear error message ✅

---

#### 3. Implement authentication manager
- [x] Create `src/auth.py`
- [x] Initialize `TelegramClient` with API credentials
- [x] Handle first-time interactive auth (phone code + 2FA)
- [x] Implement session persistence with 0600 file permissions
- [x] Handle session reuse on subsequent runs
- [x] Add reconnection logic

**Validation:** ✅ Ready for manual testing
- First run: prompts for phone code and creates session
- Second run: connects without prompts
- Manual test: delete session file → re-auth works

---

### Phase 2: Message Monitoring & Filtering (Days 3-4)

#### 4. Implement message listener
- [x] Integrated into `main.py`
- [x] Register `NewMessage` event handler with `incoming=True`
- [x] Extract message metadata: chat_id, message_id, sender, text, entities, reply_to
- [x] Normalize chat type detection (private, group, channel)
- [x] Handle service message detection
- [x] Add error handling for malformed messages

**Validation:** ✅ Ready for manual testing
- Send test DM → listener captures and logs metadata
- Send group message → listener captures and logs metadata
- Verify outgoing messages are ignored

---

#### 5. Implement trigger detection engine
- [x] Create `src/triggers.py`
- [x] Implement DM trigger: private chat + not self
- [x] Implement mention trigger: `@username` or mention entity
- [x] Implement reply trigger: fetch replied message, check if from self
- [x] Implement exclusions: self-messages, service messages
- [x] Return `(should_alert, trigger_type)` tuple

**Validation:** ✅ Ready for manual testing
- Unit tests for all trigger conditions (deferred)
- Manual test: send DM → returns `(True, "DM")`
- Manual test: mention in group → returns `(True, "Mention")`
- Manual test: reply to own message → returns `(True, "Reply")`
- Manual test: self-message → returns `(False, None)`

---

### Phase 3: Alert Delivery (Day 5)

#### 6. Implement alert formatter
- [x] Create `src/formatter.py`
- [x] Build alert message with emoji, trigger type, chat name, sender, timestamp
- [x] Generate deep links (private: `tg://openmessage`, groups: `tg://openmessage`, channels: `https://t.me/c/`)
- [x] Truncate message preview to 120 characters
- [x] Handle media-only messages with placeholder

**Validation:** ✅ Ready for manual testing
- Unit tests for formatting logic (deferred)
- Manual test: format DM alert → verify all fields present and formatted correctly

---

#### 7. Implement notification sink
- [x] Create `src/notifier.py`
- [x] Send formatted message to "me" (Saved Messages)
- [x] Implement retry logic (3 attempts, exponential backoff)
- [x] Add rate limiting (1 alert/second)
- [x] Log delivery failures

**Validation:** ✅ Ready for manual testing
- Manual test: trigger alert → message appears in Saved Messages
- Manual test: simulate network error → retries occur

---

### Phase 4: State Management & Deduplication (Day 6)

#### 8. Implement state manager
- [x] Create `src/state.py`
- [x] Define JSON schema: `{processed_messages: {}, last_cleanup: timestamp}`
- [x] Implement `is_processed(chat_id, message_id)` check
- [x] Implement `mark_processed(chat_id, message_id, trigger_type)` with atomic write
- [x] Load state on startup (create empty if missing)
- [x] Handle corrupted state (backup and reinitialize)

**Validation:** ✅ Ready for manual testing
- Unit tests for state operations (deferred)
- Manual test: send duplicate message → second occurrence skipped

---

#### 9. Implement state cleanup
- [x] Add cleanup logic: remove entries older than 30 days
- [x] Trigger cleanup every 24 hours
- [x] Update `last_cleanup` timestamp

**Validation:** ✅ Implemented
- Unit test: old entries are removed (deferred)
- Manual test: verify state file size remains bounded

---

### Phase 5: Integration & Reliability (Day 7)

#### 10. Integrate all components in main loop
- [x] Create `main.py`
- [x] Initialize config, auth, state manager
- [x] Start message listener
- [x] Wire trigger detection → state check → alert delivery pipeline
- [x] Handle graceful shutdown (SIGINT/SIGTERM)

**Validation:** ✅ Ready for end-to-end testing
- End-to-end test: send DM → alert in Saved Messages
- End-to-end test: send mention → alert in Saved Messages
- End-to-end test: reply to own message → alert in Saved Messages

---

#### 11. Implement health monitoring and logging
- [x] Integrated into `main.py` (Metrics class)
- [x] Log startup message with config summary
- [x] Implement hourly heartbeat with metrics (uptime, messages, alerts)
- [x] Log connection/disconnection events
- [x] Track metrics: messages received, alerts sent by type, deduplication hits
- [x] Ensure no message content or credentials are logged

**Validation:** ✅ Implemented
- Manual test: check logs contain heartbeat after 1 hour
- Manual test: disconnect network → reconnection logged

---

### Phase 6: Testing & Validation (Days 8-9)

#### 12. Write unit tests
- [ ] Test trigger logic (all conditions)
- [ ] Test alert formatting
- [ ] Test state management (deduplication, persistence)
- [ ] Test configuration validation
- [ ] Target: >80% code coverage

**Validation:** `pytest` all tests pass

---

#### 13. Write integration tests
- [ ] Mock Telethon client with test events
- [ ] Test end-to-end flow: message → filter → state → alert
- [ ] Test duplicate message handling
- [ ] Test error recovery (malformed messages, state corruption)

**Validation:** Integration test suite passes

---

#### 14. Manual acceptance testing
- [ ] Mute all Telegram chats
- [ ] Send DM → verify alert received within 5 seconds
- [ ] Mention in group → verify alert received
- [ ] Reply to own message → verify alert received
- [ ] Send self-message → verify NO alert
- [ ] Send duplicate qualifying message → verify single alert only
- [ ] Disconnect network → verify reconnection and alert delivery resume

**Validation:** All acceptance criteria from README pass

---

### Phase 7: Documentation & 7-Day Test (Days 10-17)

#### 15. Create user documentation
- [x] Created `SETUP.md` with comprehensive setup instructions
- [x] Document environment variables
- [x] Add troubleshooting section
- [x] Include example `.env` configuration

**Validation:** ✅ Fresh setup following docs succeeds

---

#### 16. Prepare for deployment
- [x] Documented in `SETUP.md`: nohup, screen, systemd options
- [x] Document how to run as background process
- [x] Add monitoring recommendations

**Validation:** ✅ Documentation complete

---

#### 17. Run 7-day continuous operation test
- [ ] Start service
- [ ] Monitor logs daily for errors
- [ ] Send test messages periodically
- [ ] Verify alerts continue working
- [ ] Check for memory leaks or performance degradation

**Validation:**
- Service runs for 7 days without crashes
- All test alerts delivered successfully
- No manual intervention required

---

## Dependencies & Parallelization

**Parallel tracks:**
- Tasks 1-3 can proceed sequentially (foundation)
- Tasks 4-5 depend on task 3 (auth must work first)
- Tasks 6-7 can be developed in parallel with task 8
- Task 9 depends on task 8
- Task 10 requires all previous tasks
- Tasks 12-13 can be written in parallel with development (TDD approach)

**Critical path:** 1 → 2 → 3 → 4 → 5 → 10 → 14 → 17

---

## Risk Mitigation During Implementation

| Risk | Task | Mitigation |
|------|------|------------|
| Auth complexity | Task 3 | Test with real Telegram account early |
| Reply detection fails | Task 5 | Manual testing with various chat types |
| State corruption | Task 8 | Implement atomic writes and backups |
| Silent failures | Task 11 | Comprehensive logging from day 1 |
| Long-term stability | Task 17 | Extended testing before marking complete |

---

## Definition of Done

Each task is complete when:
- ✅ Code is written and follows Python best practices (PEP 8)
- ✅ Validation steps pass
- ✅ No new errors or warnings in logs
- ✅ Changes are committed with clear commit message
