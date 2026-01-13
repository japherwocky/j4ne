#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_USER="j4ne"
DEPLOY_DIR="/opt/j4ne"
SOURCE_DIR="${SOURCE_DIR:-/tmp/j4ne}"
SERVICE_NAME="j4ne"
DOMAIN="j4ne.pearachute.com"

echo -e "${GREEN}🚀 Installing J4NE Chat Bot to production${NC}"
echo "Source: $SOURCE_DIR"
echo "Deploy: $DEPLOY_DIR"
echo "Domain: $DOMAIN"
echo "User: $DEPLOY_USER"
echo ""

# Function to check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${RED}This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

# Function to create user with SSH key
create_user() {
    echo -e "${YELLOW}👤 Setting up deployment user and SSH key...${NC}"

    # Create user if not exists
    if ! getent passwd "$DEPLOY_USER" > /dev/null 2>&1; then
        useradd --system --home $DEPLOY_DIR --shell /bin/bash $DEPLOY_USER
        echo "User $DEPLOY_USER created"
    else
        echo "User $DEPLOY_USER already exists"
    fi

    # Ensure home directory exists and has correct ownership
    mkdir -p $DEPLOY_DIR
    chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_DIR

    # Create .ssh directory
    mkdir -p $DEPLOY_DIR/.ssh
    chmod 700 $DEPLOY_DIR/.ssh
    chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_DIR/.ssh

    # Generate SSH key if not exists
    SSH_KEY="$DEPLOY_DIR/.ssh/id_ed25519"
    if [ ! -f "$SSH_KEY" ]; then
        echo -e "${BLUE}🔑 Generating ED25519 SSH key for $DEPLOY_USER...${NC}"
        sudo -u $DEPLOY_USER ssh-keygen -t ed25519 -f $SSH_KEY -N "" -C "$DEPLOY_USER@$DOMAIN"
    else
        echo "SSH key already exists at $SSH_KEY"
    fi

    # Display public key (for adding to GitHub)
    echo ""
    echo -e "${GREEN}📋 Add this public key to GitHub as a deploy key:${NC}"
    echo ""
    cat $SSH_KEY.pub
    echo ""
}

# Function to copy repo from source
copy_repo() {
    echo -e "${YELLOW}📥 Copying repository from $SOURCE_DIR...${NC}"

    if [ ! -d "$SOURCE_DIR" ]; then
        echo -e "${RED}Source directory $SOURCE_DIR does not exist${NC}"
        exit 1
    fi

    if [ -d "$DEPLOY_DIR" ]; then
        echo "Removing existing $DEPLOY_DIR..."
        rm -rf $DEPLOY_DIR
    fi

    cp -r $SOURCE_DIR $DEPLOY_DIR
    chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_DIR
    echo "Repository copied to $DEPLOY_DIR"
}

# Function to setup virtual environment
setup_virtualenv() {
    echo -e "${YELLOW}🐍 Setting up Python virtual environment...${NC}"

    if [ -f "$DEPLOY_DIR/venv/bin/python" ]; then
        echo "Virtualenv already exists"
    else
        sudo -u $DEPLOY_USER python3 -m venv $DEPLOY_DIR/venv
        echo "Virtualenv created"
    fi
}

# Function to install dependencies
install_dependencies() {
    echo -e "${YELLOW}📦 Installing system dependencies...${NC}"
    apt-get update
    apt-get install -y python3-venv python3-pip nginx git curl

    # Install certbot via snap (recommended by certbot)
    echo -e "${YELLOW}📦 Installing certbot via snap...${NC}"
    if ! command -v snap &>/dev/null; then
        apt-get install -y snapd
    fi
    
    # Ensure snap is up to date
    snap install core; snap refresh core
    
    # Install certbot
    if ! command -v certbot &>/dev/null; then
        snap install --classic certbot
        ln -sf /snap/bin/certbot /usr/bin/certbot
        echo "Certbot installed via snap"
    else
        echo "Certbot already installed"
    fi

    echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
    sudo -u $DEPLOY_USER $DEPLOY_DIR/venv/bin/pip install --upgrade pip
    sudo -u $DEPLOY_USER $DEPLOY_DIR/venv/bin/pip install -r $DEPLOY_DIR/requirements.txt
}

# Function to setup environment configuration
setup_env() {
    echo -e "${YELLOW}⚙️ Setting up environment configuration...${NC}"

    # Copy example environment file if .env doesn't exist
    if [ ! -f "$DEPLOY_DIR/.env" ]; then
        sudo -u $DEPLOY_USER cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env
        echo "Created .env from .env.example"
        echo "Please edit $DEPLOY_DIR/.env to configure your API keys"
    else
        echo ".env file already exists, preserving configuration"
    fi
}

# Function to setup systemd service
setup_systemd() {
    echo -e "${YELLOW}⚙️ Setting up systemd service...${NC}"
    cp $DEPLOY_DIR/sys/systemd/j4ne.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable j4ne
    # Restart service if it's already running to pick up config changes
    if systemctl is-active --quiet j4ne; then
        systemctl restart j4ne
        echo "J4NE service restarted with new configuration"
    fi
    echo "Systemd service configured"
}

# Function to setup nginx
setup_nginx() {
    echo -e "${YELLOW}🌐 Setting up nginx...${NC}"
    # Install nginx config but don't test/reload yet (certs don't exist)
    cp $DEPLOY_DIR/sys/nginx/j4ne.pearachute.com.conf /etc/nginx/sites-available/
    ln -sf /etc/nginx/sites-available/j4ne.pearachute.com.conf /etc/nginx/sites-enabled/
    echo "Nginx config installed (SSL pending certbot)"
}

# Function to setup sudoers for j4ne user
setup_sudoers() {
    echo -e "${YELLOW}🔐 Setting up sudoers permissions...${NC}"

    # Allow j4ne user to restart service without password
    echo "j4ne ALL=(ALL) NOPASSWD: /bin/systemctl restart j4ne" > /etc/sudoers.d/j4ne-restart
    chmod 440 /etc/sudoers.d/j4ne-restart

    echo "Sudoers configured - j4ne can restart service without password"
}

# Function to setup SSL with Let's Encrypt
setup_ssl() {
    echo -e "${YELLOW}🔒 Setting up SSL with Let's Encrypt...${NC}"
    
    # First, temporarily disable nginx config to get certificates
    echo "Temporarily disabling nginx SSL config for certificate generation..."

    # Start nginx if it's not running
    if ! systemctl is-active --quiet nginx; then
        systemctl start nginx
    fi

    # Disable any existing j4ne configs
    if [ -L "/etc/nginx/sites-enabled/$DOMAIN.conf" ] || [ -f "/etc/nginx/sites-enabled/$DOMAIN.conf" ]; then
        rm -f /etc/nginx/sites-enabled/$DOMAIN.conf
        echo "Disabled existing j4ne nginx config"
    fi

    # Create a simple nginx config for HTTP only to pass certbot challenges
    cat > /etc/nginx/sites-available/$DOMAIN-http.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF
    ln -sf /etc/nginx/sites-available/$DOMAIN-http.conf /etc/nginx/sites-enabled/

    # Test and reload nginx
    if nginx -t; then
        systemctl reload nginx
        echo "Nginx reloaded successfully"
    else
        echo "Nginx configuration test failed"
        return 1
    fi
    
    # Get certificates using webroot method (more reliable than nginx plugin)
    echo "Obtaining SSL certificates..."
    certbot certonly --webroot -w /var/www/html \
        --non-interactive --agree-tos --email admin@$DOMAIN \
        -d $DOMAIN && {
        echo "SSL certificates obtained successfully"
    } || {
        echo -e "${RED}Certificate setup failed. You may need to run certbot manually:${NC}"
        echo "certbot certonly --webroot -w /var/www/html -d $DOMAIN"
        # Restore original config and exit
        rm -f /etc/nginx/sites-enabled/$DOMAIN-http.conf
        if [ -f "/etc/nginx/sites-enabled/$DOMAIN.conf.bak" ]; then
            mv /etc/nginx/sites-enabled/$DOMAIN.conf.bak /etc/nginx/sites-enabled/$DOMAIN.conf
        fi
        return 1
    }
    
    # Remove temporary HTTP config
    rm -f /etc/nginx/sites-enabled/$DOMAIN-http.conf
    rm -f /etc/nginx/sites-available/$DOMAIN-http.conf

    # Restore original nginx config with SSL
    if [ -f "/etc/nginx/sites-enabled/$DOMAIN.conf.bak" ]; then
        mv /etc/nginx/sites-enabled/$DOMAIN.conf.bak /etc/nginx/sites-enabled/$DOMAIN.conf
    else
        # Re-enable j4ne config if it wasn't backed up
        ln -sf /etc/nginx/sites-available/$DOMAIN.conf /etc/nginx/sites-enabled/
    fi
    
    # Test and reload nginx with SSL config
    nginx -t && systemctl reload nginx && {
        echo "Nginx reloaded with SSL configuration"
    } || {
        echo -e "${RED}Nginx configuration test failed after SSL setup${NC}"
        return 1
    }
    
    # Setup automatic certificate renewal
    echo "Setting up automatic certificate renewal..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'systemctl reload nginx'") | crontab -
    
    echo "SSL setup complete!"
}

# Function to start service
start_service() {
    echo -e "${GREEN}🚀 Starting j4ne service...${NC}"
    systemctl restart j4ne  # Use restart to ensure it picks up any config changes
    systemctl status j4ne --no-pager
}

# Main installation flow
main() {
    check_root

    echo -e "${GREEN}Step 1: User setup with SSH key${NC}"
    create_user

    echo -e "${GREEN}Step 2: Copy repository${NC}"
    copy_repo

    echo -e "${GREEN}Step 3: Application setup${NC}"
    setup_virtualenv
    install_dependencies
    setup_env

    echo -e "${GREEN}Step 4: Service configuration${NC}"
    setup_systemd
    setup_nginx
    setup_sudoers

    echo -e "${GREEN}Step 5: SSL setup${NC}"
    setup_ssl

    echo -e "${GREEN}Step 6: Start service${NC}"
    start_service

    echo ""
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Add SSH public key above to GitHub as a deploy key"
    echo "2. Edit $DEPLOY_DIR/.env to configure your API keys"
    echo "   - OPENCODE_ZEN_API_KEY (required for AI responses)"
    echo "   - SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET (for Slack HTTP integration)"
    echo "   - IRC configuration variables (for IRC integration)"
    echo "3. Test deployment with: sudo -u j4ne $DEPLOY_DIR/sys/scripts/deploy.sh"
    echo ""
    echo "Your J4NE bot is now running at: https://$DOMAIN"
    echo ""
    echo "Useful commands:"
    echo "  Check service status: systemctl status j4ne"
    echo "  View logs: journalctl -u j4ne -f"
    echo "  Restart service: sudo systemctl restart j4ne"
    echo "  Update application: sudo -u j4ne $DEPLOY_DIR/sys/scripts/deploy.sh"
}

# Run installation
main "$@"