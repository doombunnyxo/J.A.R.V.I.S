# Discord Bot Systemd Service Setup

This guide will help you set up the Discord bot as a systemd service on Linux.

## Prerequisites

1. Linux system with systemd
2. Python 3.8+ installed
3. Bot code deployed to `/home/elizk/discord-bot/`
4. Virtual environment set up with dependencies installed
5. `.env` file with all required API keys

## Installation Steps

### 1. Update the Service File Paths

Edit `discord-bot.service` and update these paths to match your setup:

```ini
User=your_username
Group=your_username
WorkingDirectory=/path/to/your/discord-bot
Environment=PATH=/path/to/your/discord-bot/venv/bin
ExecStart=/path/to/your/discord-bot/venv/bin/python /path/to/your/discord-bot/main.py
ReadWritePaths=/path/to/your/discord-bot/data
```

### 2. Copy Service File

```bash
# Copy the service file to systemd directory
sudo cp discord-bot.service /etc/systemd/system/

# Set correct permissions
sudo chmod 644 /etc/systemd/system/discord-bot.service
```

### 3. Create Data Directory

```bash
# Ensure data directory exists and has correct permissions
mkdir -p /home/elizk/discord-bot/data
chmod 755 /home/elizk/discord-bot/data
```

### 4. Enable and Start Service

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable discord-bot

# Start the service
sudo systemctl start discord-bot
```

## Service Management Commands

### Check Service Status
```bash
sudo systemctl status discord-bot
```

### View Service Logs
```bash
# View recent logs
sudo journalctl -u discord-bot

# Follow live logs
sudo journalctl -u discord-bot -f

# View logs from last boot
sudo journalctl -u discord-bot -b
```

### Start/Stop/Restart Service
```bash
# Start service
sudo systemctl start discord-bot

# Stop service
sudo systemctl stop discord-bot

# Restart service
sudo systemctl restart discord-bot

# Reload service configuration
sudo systemctl reload discord-bot
```

### Disable Service
```bash
# Disable auto-start on boot
sudo systemctl disable discord-bot

# Stop and disable
sudo systemctl stop discord-bot
sudo systemctl disable discord-bot
```

## Security Features

The service file includes several security hardening features:

- **NoNewPrivileges**: Prevents privilege escalation
- **PrivateTmp**: Provides private `/tmp` directory
- **ProtectSystem**: Makes system directories read-only
- **ProtectHome**: Restricts access to user home directories
- **ReadWritePaths**: Only allows writing to the bot's data directory
- **Resource Limits**: Limits memory usage and file descriptors

## Troubleshooting

### Service Won't Start
1. Check service status: `sudo systemctl status discord-bot`
2. Check logs: `sudo journalctl -u discord-bot`
3. Verify file paths in service file
4. Ensure Python virtual environment is working
5. Check file permissions

### Permission Issues
```bash
# Fix ownership of bot directory
sudo chown -R elizk:elizk /home/elizk/discord-bot/

# Fix permissions
chmod +x /home/elizk/discord-bot/main.py
chmod -R 755 /home/elizk/discord-bot/
```

### Environment Variables
If the service can't find environment variables:
1. Ensure `.env` file is in the working directory
2. Or add environment variables directly to service file:
```ini
Environment="DISCORD_TOKEN=your_token_here"
Environment="GROQ_API_KEY=your_key_here"
```

### Virtual Environment Issues
Verify virtual environment paths:
```bash
# Check Python path
which python
/home/elizk/discord-bot/venv/bin/python

# Test bot manually
cd /home/elizk/discord-bot
./venv/bin/python main.py
```

## Updating the Bot

When updating bot code:
```bash
# Stop service
sudo systemctl stop discord-bot

# Update code (git pull, etc.)
cd /home/elizk/discord-bot
git pull

# Install any new dependencies
./venv/bin/pip install -r requirements.txt

# Start service
sudo systemctl start discord-bot
```

## Monitoring

### Service Health Check
```bash
# One-liner to check if service is running
systemctl is-active discord-bot && echo "Bot is running" || echo "Bot is not running"
```

### Resource Usage
```bash
# Check memory usage
sudo systemctl show discord-bot --property=MemoryCurrent

# Check CPU usage
top -p $(systemctl show discord-bot --property=MainPID --value)
```