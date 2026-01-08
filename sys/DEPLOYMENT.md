# Production Deployment Guide

This guide will help you deploy the J4NE Chat Bot to production on an Ubuntu LTS server with nginx.

## Prerequisites

- Ubuntu LTS server with root/sudo access
- Domain name pointing to your server (e.g., `j4ne.yourdomain.com`)
- Git installed
- OpenCode Zen API key (get it from https://opencode.ai/auth)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/j4ne.git /tmp/j4ne
   ```

2. Make scripts executable:
   ```bash
   chmod +x sys/scripts/*.sh
   ```

3. Run the installation script:
   ```bash
   sudo DOMAIN=j4ne.yourdomain.com EMAIL=admin@yourdomain.com sys/scripts/install.sh
   ```

## Manual Deployment Steps

If you prefer to deploy manually, follow these steps:

### 1. System Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y python3-venv python3-pip nginx certbot python3-certbot-nginx git curl

# Install Node.js 20 (optional, only needed if building frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
sudo apt-get install -y nodejs
```

### 2. Application User

```bash
# Create system user
sudo useradd --system --home /opt/j4ne --shell /bin/bash j4ne

# Create directories
sudo mkdir -p /opt/j4ne/{data,logs}
sudo mkdir -p /var/www/certbot
sudo chown -R j4ne:j4ne /opt/j4ne
```

### 3. Application Setup

```bash
# Clone repository
sudo -u j4ne git clone https://github.com/yourusername/j4ne.git /opt/j4ne

# Setup virtual environment
sudo -u j4ne python3 -m venv /opt/j4ne/venv

# Install Python dependencies
sudo -u j4ne /opt/j4ne/venv/bin/pip install --upgrade pip
sudo -u j4ne /opt/j4ne/venv/bin/pip install -r /opt/j4ne/requirements.txt
```

### 4. Environment Configuration

```bash
# Copy environment template
sudo -u j4ne cp /opt/j4ne/sys/config/production.env /opt/j4ne/.env

# Edit the configuration
sudo -u j4ne nano /opt/j4ne/.env
```

Configure the following required settings:
- `OPENCODE_ZEN_API_KEY` - Your OpenCode Zen API key
- `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` (for Slack integration)
- IRC configuration variables (for IRC integration)

### 5. Systemd Service

```bash
# Copy service file
sudo cp /opt/j4ne/sys/systemd/j4ne.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable j4ne
sudo systemctl start j4ne
```

### 6. Nginx Configuration

```bash
# Copy nginx config (replace example.com with your domain)
sudo cp /opt/j4ne/sys/nginx/j4ne.example.com.conf /etc/nginx/sites-available/j4ne.yourdomain.com.conf
sudo nano /etc/nginx/sites-available/j4ne.yourdomain.com.conf  # Edit domain name

# Enable the site
sudo ln -sf /etc/nginx/sites-available/j4ne.yourdomain.com.conf /etc/nginx/sites-enabled/

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL Certificate

```bash
# Run SSL setup script
sudo /opt/j4ne/sys/scripts/setup-ssl.sh j4ne.yourdomain.com admin@yourdomain.com

# Or manually:
sudo certbot --nginx -d j4ne.yourdomain.com
```

## Configuration

### Environment Variables

The main configuration is in `/opt/j4ne/.env`. Key settings include:

#### Required
- `OPENCODE_ZEN_API_KEY` - API key for AI responses

#### Slack Integration (Optional)
- `SLACK_BOT_TOKEN` - Bot User OAuth Token (starts with `xoxb-`)
- `SLACK_APP_TOKEN` - App-Level Token (starts with `xapp-`)

#### IRC Integration (Optional)
- `IRC_SERVER` - IRC server address (default: `irc.libera.chat`)
- `IRC_PORT` - IRC port (default: `6667`)
- `IRC_NICKNAME` - Bot nickname (default: `j4ne-bot`)
- `IRC_CHANNELS` - Comma-separated list of channels to join

### Slack App Setup

If using Slack integration:

1. Go to https://api.slack.com/apps
2. Create a new app "From scratch"
3. Enable **Socket Mode** in the app settings
4. Add the following Bot Token Scopes:
   - `chat:write` - Send messages
   - `users:read` - Get user info
   - `channels:read` - Read channel info
5. Install the app to your workspace
6. Copy the tokens to your `.env` file

### Service Management

```bash
# Check service status
sudo systemctl status j4ne

# View logs
sudo journalctl -u j4ne -f

# Restart service
sudo systemctl restart j4ne

# Stop service
sudo systemctl stop j4ne
```

## Maintenance

### Updates

To update the application:

```bash
# Pull latest changes
cd /opt/j4ne
sudo -u j4ne git pull

# Restart service
sudo systemctl restart j4ne
```

Or use the deployment script:

```bash
sudo -u j4ne /opt/j4ne/sys/scripts/deploy.sh
```

### Logging

```bash
# View all logs
sudo journalctl -u j4ne

# View logs since last restart
sudo journalctl -u j4ne --since '5 minutes ago'

# View only errors
sudo journalctl -u j4ne -p err
```

### Backup

```bash
# Backup data directory
sudo cp -r /opt/j4ne/data /opt/j4ne/data.backup.$(date +%Y%m%d)
```

### SSL Certificate Renewal

Let's Encrypt certificates are automatically renewed via cron. To test renewal:

```bash
sudo certbot renew --dry-run
```

## Directory Structure

```
/opt/j4ne/
├── j4ne.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── venv/                      # Python virtual environment
├── sys/                       # Deployment configuration
│   ├── nginx/                # Nginx configs
│   ├── systemd/              # Service files
│   ├── scripts/              # Deployment scripts
│   └── config/               # Environment templates
├── data/                     # Application data
├── logs/                     # Log files
└── .env                      # Environment variables (production)
```

## Security Considerations

1. **API Keys**: Keep all API keys confidential and never commit them to version control
2. **Regular Updates**: Keep system packages and dependencies updated
3. **Backups**: Regularly backup the data directory
4. **Firewall**: Configure UFW or similar firewall
5. **Monitoring**: Set up monitoring for service health

## Troubleshooting

### Service Won't Start

Check logs for errors:
```bash
sudo journalctl -u j4ne -f
```

Common issues:
- Missing dependencies: `sudo -u j4ne /opt/j4ne/venv/bin/pip install -r /opt/j4ne/requirements.txt`
- Permissions: Ensure `/opt/j4ne` is owned by `j4ne` user
- Configuration: Check `/opt/j4ne/.env` for required API keys

### Nginx Issues

Test nginx configuration:
```bash
sudo nginx -t
```

Check nginx logs:
```bash
sudo tail -f /var/log/nginx/j4ne.yourdomain.com.error.log
```

### SSL Issues

Check certificate status:
```bash
sudo certbot certificates
```

Request new certificate:
```bash
sudo certbot --nginx -d j4ne.yourdomain.com --force-renewal
```

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review service logs: `sudo journalctl -u j4ne`
3. Review nginx logs: `sudo tail -f /var/log/nginx/j4ne.yourdomain.com.error.log`
4. Check the GitHub repository for known issues
