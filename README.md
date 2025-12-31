# Telegram Priority Notifier

A self-hosted Telegram notification system that monitors your account for important messages and sends priority alerts when you receive direct messages, mentions, or replies - even in muted chats.

## Features

- **Smart Alert Triggers**

  - Direct messages (DMs) from any user
  - @mentions of your username
  - Replies to your messages in any chat

- **Priority Contacts & Mute Lists**

  - Whitelist mode: Only receive alerts from specific contacts
  - Blacklist mode: Mute specific chats/users from triggering alerts
  - Flexible filtering that works across all chat types

- **Snooze System**

  - Temporarily pause all notifications
  - Queue mode: Collect alerts during snooze and deliver them when you're back
  - Drop mode: Silently ignore alerts during snooze
  - Automatic expiration with customizable durations

- **Reliability**
  - Automatic reconnection on network failures
  - Message deduplication (no duplicate alerts)
  - State persistence across restarts
  - Hourly heartbeat logging for monitoring

## Quick Start

### One-Command Setup

```bash
git clone https://github.com/nduongg04/telegram-mention-notification.git
cd tele-noti
./run.sh
```

The setup script will:

1. Check for Python 3.8+
2. Create a virtual environment
3. Install dependencies
4. Guide you through configuration
5. Start the notifier

### Manual Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/nduongg04/telegram-mention-notification.git
   cd tele-noti
   ```

2. **Create virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the notifier**
   ```bash
   python main.py
   ```

## Configuration

### Required Credentials

You'll need to obtain the following:

| Variable             | Description           | How to Get                                           |
| -------------------- | --------------------- | ---------------------------------------------------- |
| `TELEGRAM_API_ID`    | Telegram API ID       | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_API_HASH`  | Telegram API Hash     | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_PHONE`     | Your phone number     | Format: `+1234567890`                                |
| `TELEGRAM_BOT_TOKEN` | Bot token             | Create via [@BotFather](https://t.me/BotFather)      |
| `TELEGRAM_CHAT_ID`   | Chat ID with your bot | See instructions below                               |

### Getting Your Chat ID

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Start a chat with your new bot
3. Send any message to the bot
4. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Find the `"chat":{"id":YOUR_CHAT_ID}` in the response

### Optional Settings

| Variable       | Default                 | Description                                 |
| -------------- | ----------------------- | ------------------------------------------- |
| `SESSION_FILE` | `telegram_session.json` | User session file path                      |
| `STATE_FILE`   | `state.json`            | State persistence file path                 |
| `LOG_LEVEL`    | `INFO`                  | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Bot Commands

Control the notifier by sending commands to your bot:

### Status

| Command   | Description                      |
| --------- | -------------------------------- |
| `/start`  | Welcome message and introduction |
| `/help`   | Show all available commands      |
| `/status` | Current notifier status overview |

### Snooze

| Command                      | Description                             |
| ---------------------------- | --------------------------------------- |
| `/snooze <duration>`         | Snooze alerts (e.g., `30m`, `2h`, `1d`) |
| `/snooze --queue <duration>` | Snooze with alert queueing              |
| `/snooze status`             | Check current snooze status             |
| `/unsnooze`                  | End snooze and deliver queued alerts    |

### Priority Contacts

| Command                  | Description                                       |
| ------------------------ | ------------------------------------------------- |
| `/priority mode <mode>`  | Set filter mode (`whitelist`, `blacklist`, `off`) |
| `/priority add @user`    | Add user to priority list                         |
| `/priority remove @user` | Remove user from priority list                    |
| `/priority list`         | Show current priority list                        |

### Mute List

| Command         | Description           |
| --------------- | --------------------- |
| `/mute @chat`   | Mute a chat or user   |
| `/unmute @chat` | Unmute a chat or user |
| `/listmuted`    | Show muted list       |

## Alert Format

Alerts are clearly formatted with trigger type and message context:

```
🔔 [DM]
Chat: John Doe
From: John Doe (@johndoe)
Time: 2025-01-15 14:30:00
Link: https://t.me/johndoe

Preview:
Hey, are you available for a quick call?
```

Bot responses use a distinct 🤖 prefix to differentiate from alerts.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Priority Notifier                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  User Client │    │  Bot Client  │    │    State     │  │
│  │  (MTProto)   │    │  (Commands)  │    │   Manager    │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Message Handler                    │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │
│  │  │ Snooze  │→ │Priority │→ │ Trigger │→ │  Dedup  │  │  │
│  │  │ Check   │  │ Filter  │  │ Engine  │  │  Check  │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │
│  └──────────────────────────┬───────────────────────────┘  │
│                             │                              │
│                             ▼                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Alert Formatter & Notifier               │  │
│  │         (Sends alerts via Telegram Bot API)           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/tele-noti.service`:

```ini
[Unit]
Description=Telegram Priority Notifier
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/tele-noti
Environment=PATH=/path/to/tele-noti/venv/bin
ExecStart=/path/to/tele-noti/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable tele-noti
sudo systemctl start tele-noti
```

### Docker (Coming Soon)

Docker support is planned for a future release.

## Development

### Project Structure

```
tele-noti/
├── main.py              # Application entry point
├── run.sh               # Setup and run script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── src/
    ├── auth.py          # Telegram authentication
    ├── commands.py      # Bot command handlers
    ├── config.py        # Configuration loader
    ├── formatter.py     # Alert message formatter
    ├── notifier.py      # Notification delivery
    ├── state.py         # State persistence
    └── triggers.py      # Alert trigger logic
```

### Running in Development

```bash
# Use DEBUG log level for verbose output
LOG_LEVEL=DEBUG python main.py
```

## Security Notes

- Session credentials are stored locally in session files
- Never commit `.env` or session files to version control
- The bot only reads messages; it never modifies or deletes anything
- All communication uses Telegram's encrypted MTProto protocol

## Troubleshooting

### "Could not resolve: @username"

- Ensure the username exists and you have interacted with them before
- Try using the full username with @ prefix

### Commands not responding

- Make sure you're sending commands to the bot, not a regular chat
- Verify the bot token and chat ID are correct
- Check logs for error messages

### Session expired

- Delete `telegram_session.json` and `bot_session.session`
- Run the application again to re-authenticate

### Rate limiting

- The notifier implements automatic rate limiting
- If you see 429 errors, wait a few minutes before retrying

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- Built with [Telethon](https://github.com/LonamiWebs/Telethon) - Pure Python MTProto API
- Inspired by the need for better Telegram notification management
