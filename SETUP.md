# Telegram Priority Notifier - Setup Guide

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- Telegram API credentials (get from https://my.telegram.org/apps)
- Your phone number with Telegram account

### 2. Installation

```bash
# Navigate to project directory
cd tele-noti

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Copy your `API ID` and `API Hash`

### 4. Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your credentials
nano .env  # or use any text editor
```

Example `.env` file:
```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+1234567890

# Optional - these have defaults
SESSION_FILE=telegram_session.json
STATE_FILE=state.json
LOG_LEVEL=INFO
```

### 5. First Run

```bash
# Make the script executable (optional)
chmod +x main.py

# Run the application
python main.py
```

**First-time authentication:**
- You'll be prompted to enter the verification code sent to your Telegram
- If you have 2FA enabled, you'll also need to enter your password
- Your session will be saved, so future runs won't require re-authentication

### 6. Verify It's Working

1. Mute all your Telegram chats
2. Ask a friend to:
   - Send you a direct message
   - Mention you in a group chat
   - Reply to one of your messages
3. Check your Telegram "Saved Messages" for alert notifications

## Running in Background

### Option 1: Using nohup (Linux/macOS)

```bash
nohup python main.py > notifier.log 2>&1 &

# View logs
tail -f notifier.log

# Stop the process
ps aux | grep main.py
kill <PID>
```

### Option 2: Using screen (Linux/macOS)

```bash
# Start a screen session
screen -S telegram-notifier

# Run the application
python main.py

# Detach from screen: Press Ctrl+A then D

# Reattach to screen
screen -r telegram-notifier

# Kill the screen session
screen -X -S telegram-notifier quit
```

### Option 3: Using systemd (Linux)

Create `/etc/systemd/system/telegram-notifier.service`:

```ini
[Unit]
Description=Telegram Priority Notifier
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/tele-noti
Environment="PATH=/path/to/tele-noti/venv/bin"
ExecStart=/path/to/tele-noti/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-notifier
sudo systemctl start telegram-notifier

# Check status
sudo systemctl status telegram-notifier

# View logs
sudo journalctl -u telegram-notifier -f
```

## Configuration Options

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_API_ID` | Yes | - | Your Telegram API ID |
| `TELEGRAM_API_HASH` | Yes | - | Your Telegram API Hash |
| `TELEGRAM_PHONE` | Yes | - | Your phone number with country code |
| `SESSION_FILE` | No | `telegram_session.json` | Path to session file |
| `STATE_FILE` | No | `state.json` | Path to deduplication state file |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Troubleshooting

### "Required environment variable not set"

Make sure your `.env` file is in the same directory as `main.py` and contains all required variables.

### Authentication fails

1. Double-check your API ID and API Hash
2. Make sure your phone number includes the country code (e.g., `+1` for US)
3. Delete the session file and try again: `rm telegram_session.json*`

### Not receiving alerts

1. Check that the application is running: `ps aux | grep main.py`
2. Check logs for errors: `tail -f notifier.log`
3. Send yourself a test DM from another account
4. Verify your Saved Messages on Telegram

### High memory usage

The state file grows over time. The system automatically cleans up entries older than 30 days, but you can manually reset it:

```bash
# Stop the application
# Remove old state
rm state.json
# Restart the application
```

## Security Notes

- **Never commit your `.env` file or session files to version control**
- Session files contain authentication tokens - protect them like passwords
- The application only reads messages, it never modifies or deletes anything
- API credentials and message content are never logged

## Support

For issues or questions, check the logs first:
- Look for ERROR or WARNING messages
- Set `LOG_LEVEL=DEBUG` for more detailed output

Common log locations:
- Foreground: displayed in terminal
- Background (`nohup`): `notifier.log`
- Systemd: `sudo journalctl -u telegram-notifier`
