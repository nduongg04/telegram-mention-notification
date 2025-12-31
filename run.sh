#!/bin/bash

# Telegram Priority Notifier - Setup and Run Script
# This script handles installation, configuration, and running the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Print colored message
print_msg() {
    echo -e "${2:-$NC}$1${NC}"
}

print_header() {
    echo ""
    print_msg "======================================" "$CYAN"
    print_msg "$1" "$CYAN"
    print_msg "======================================" "$CYAN"
    echo ""
}

print_success() {
    print_msg "✓ $1" "$GREEN"
}

print_warning() {
    print_msg "⚠ $1" "$YELLOW"
}

print_error() {
    print_msg "✗ $1" "$RED"
}

print_info() {
    print_msg "→ $1" "$BLUE"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    print_header "Checking Python Installation"

    # Try python3 first, then python
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed!"
        echo ""
        print_info "Please install Python 3.8+ from:"
        print_info "  - macOS: brew install python3"
        print_info "  - Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        print_info "  - Windows: https://www.python.org/downloads/"
        exit 1
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        print_error "Python 3.8+ is required. Found: $PYTHON_VERSION"
        exit 1
    fi

    print_success "Python $PYTHON_VERSION found ($PYTHON_CMD)"
}

# Setup virtual environment
setup_venv() {
    print_header "Setting Up Virtual Environment"

    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi

    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        print_error "Could not find virtual environment activation script"
        exit 1
    fi

    print_success "Virtual environment activated"
}

# Install dependencies
install_deps() {
    print_header "Installing Dependencies"

    print_info "Upgrading pip..."
    pip install --upgrade pip --quiet

    print_info "Installing required packages..."
    pip install -r requirements.txt --quiet

    print_success "All dependencies installed"
}

# Configure environment
configure_env() {
    print_header "Environment Configuration"

    # Check if .env exists and has valid values
    if [ -f ".env" ]; then
        # Check if it's configured (not just the example)
        if grep -q "your_api_id_here\|your_api_hash_here\|your_bot_token_here\|your_chat_id_here" .env 2>/dev/null; then
            print_warning ".env file exists but contains placeholder values"
            read -p "Do you want to reconfigure? (y/N): " RECONFIGURE
            if [[ ! "$RECONFIGURE" =~ ^[Yy]$ ]]; then
                print_info "Keeping existing .env file"
                return
            fi
        else
            print_success ".env file already configured"
            read -p "Do you want to reconfigure? (y/N): " RECONFIGURE
            if [[ ! "$RECONFIGURE" =~ ^[Yy]$ ]]; then
                return
            fi
        fi
    fi

    echo ""
    print_msg "Let's configure your Telegram credentials." "$CYAN"
    echo ""
    print_info "You'll need:"
    print_info "  1. Telegram API credentials from https://my.telegram.org/apps"
    print_info "  2. A bot token from @BotFather"
    print_info "  3. Your chat ID with the bot"
    echo ""

    # Get API ID
    while true; do
        read -p "Enter your Telegram API ID (numeric): " API_ID
        if [[ "$API_ID" =~ ^[0-9]+$ ]]; then
            break
        fi
        print_error "API ID must be a number"
    done

    # Get API Hash
    while true; do
        read -p "Enter your Telegram API Hash: " API_HASH
        if [ -n "$API_HASH" ]; then
            break
        fi
        print_error "API Hash cannot be empty"
    done

    # Get Phone Number
    while true; do
        read -p "Enter your phone number (with country code, e.g., +1234567890): " PHONE
        if [[ "$PHONE" =~ ^\+[0-9]+$ ]]; then
            break
        fi
        print_error "Phone number must start with + followed by digits"
    done

    # Get Bot Token
    echo ""
    print_info "Create a bot via @BotFather if you haven't already"
    while true; do
        read -p "Enter your Bot Token: " BOT_TOKEN
        if [[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
            break
        fi
        print_error "Invalid bot token format (should be like: 123456789:ABCdefGHI...)"
    done

    # Get Chat ID
    echo ""
    print_info "To get your chat ID:"
    print_info "  1. Start a chat with your bot on Telegram"
    print_info "  2. Send any message to the bot"
    print_info "  3. Visit: https://api.telegram.org/bot${BOT_TOKEN}/getUpdates"
    print_info "  4. Look for \"chat\":{\"id\":YOUR_CHAT_ID}"
    echo ""
    while true; do
        read -p "Enter your Chat ID (numeric, can be negative): " CHAT_ID
        if [[ "$CHAT_ID" =~ ^-?[0-9]+$ ]]; then
            break
        fi
        print_error "Chat ID must be a number (can be negative for groups)"
    done

    # Optional: Log Level
    echo ""
    read -p "Enter log level (DEBUG/INFO/WARNING/ERROR) [INFO]: " LOG_LEVEL
    LOG_LEVEL=${LOG_LEVEL:-INFO}

    # Create .env file
    cat > .env << EOF
# Telegram API Credentials
TELEGRAM_API_ID=$API_ID
TELEGRAM_API_HASH=$API_HASH
TELEGRAM_PHONE=$PHONE

# Bot Configuration
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_CHAT_ID=$CHAT_ID

# Optional Configuration
SESSION_FILE=telegram_session.json
STATE_FILE=state.json
LOG_LEVEL=$LOG_LEVEL
EOF

    print_success ".env file created successfully"
}

# Run the application
run_app() {
    print_header "Starting Telegram Priority Notifier"

    # Make sure we're in venv
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        elif [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        fi
    fi

    print_info "Starting application..."
    print_info "Press Ctrl+C to stop"
    echo ""

    python main.py
}

# Show help
show_help() {
    echo "Telegram Priority Notifier - Setup and Run Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup     - Install dependencies and configure environment"
    echo "  config    - Reconfigure environment variables"
    echo "  run       - Run the application (setup if needed)"
    echo "  start     - Alias for 'run'"
    echo "  help      - Show this help message"
    echo ""
    echo "If no command is provided, the script will run full setup and start the app."
}

# Main function
main() {
    print_msg "
╔════════════════════════════════════════════╗
║   Telegram Priority Notifier              ║
║   Setup and Run Script                    ║
╚════════════════════════════════════════════╝" "$CYAN"

    case "${1:-}" in
        setup)
            check_python
            setup_venv
            install_deps
            configure_env
            print_header "Setup Complete!"
            print_success "Run './run.sh start' to launch the application"
            ;;
        config)
            configure_env
            ;;
        run|start)
            check_python
            setup_venv
            install_deps
            if [ ! -f ".env" ] || grep -q "your_api_id_here" .env 2>/dev/null; then
                configure_env
            fi
            run_app
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            # Full setup and run
            check_python
            setup_venv
            install_deps
            configure_env
            run_app
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
