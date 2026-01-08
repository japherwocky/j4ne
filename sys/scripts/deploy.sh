#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_DIR="/opt/j4ne"

echo -e "${GREEN}🚀 Deploying J4NE Chat Bot updates${NC}"
echo "Deploy Directory: $DEPLOY_DIR"
echo ""

# Check if running as j4ne user
check_user() {
    CURRENT_USER=$(whoami)
    if [ "$CURRENT_USER" != "j4ne" ]; then
        echo -e "${RED}This script must be run as the j4ne user:${NC}"
        echo "  sudo -u j4ne $DEPLOY_DIR/sys/scripts/deploy.sh"
        exit 1
    fi
}

# Function to git pull
git_pull() {
    echo -e "${YELLOW}📥 Pulling latest changes...${NC}"

    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo "Current branch: $CURRENT_BRANCH"

    git fetch origin
    git pull origin $CURRENT_BRANCH

    echo "Code updated"
}

# Function to update dependencies (if requirements changed)
update_dependencies() {
    echo -e "${YELLOW}📦 Checking Python dependencies...${NC}"

    # Check if requirements.txt changed
    if git diff --name-only HEAD~1 HEAD | grep -q "requirements.txt"; then
        echo "Requirements changed, updating..."
        $DEPLOY_DIR/venv/bin/pip install -r $DEPLOY_DIR/requirements.txt
    else
        echo "Requirements unchanged, skipping"
    fi
}

# Function to update environment configuration
update_env() {
    echo -e "${YELLOW}⚙️ Checking environment configuration...${NC}"

    # Check if production.env template changed
    if git diff --name-only HEAD~1 HEAD | grep -q "sys/config/production.env"; then
        echo "Environment template changed, copying new template..."
        # Backup current .env
        if [ -f "$DEPLOY_DIR/.env" ]; then
            cp $DEPLOY_DIR/.env $DEPLOY_DIR/.env.backup.$(date +%Y%m%d)
            echo "Backed up existing .env file"
        fi
        # Copy new template but preserve critical values
        cp $DEPLOY_DIR/sys/config/production.env $DEPLOY_DIR/.env
        echo "Environment template updated - please review and add your API keys"
    else
        echo "Environment template unchanged"
    fi
}

# Function to restart service
restart_service() {
    echo -e "${YELLOW}🔄 Restarting j4ne service...${NC}"
    sudo systemctl restart j4ne
    sleep 2

    # Check if service is running
    if systemctl is-active --quiet j4ne; then
        echo -e "${GREEN}✅ Service restarted successfully${NC}"
    else
        echo -e "${RED}❌ Service failed to start${NC}"
        systemctl status j4ne --no-pager
        exit 1
    fi
}

# Main deployment flow
main() {
    check_user

    cd $DEPLOY_DIR

    echo -e "${GREEN}Step 1: Pull updates${NC}"
    git_pull

    echo -e "${GREEN}Step 2: Update dependencies${NC}"
    update_dependencies

    echo -e "${GREEN}Step 3: Update environment configuration${NC}"
    update_env

    echo -e "${GREEN}Step 4: Restart service${NC}"
    restart_service

    echo ""
    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo ""
    echo "Useful commands:"
    echo "  Check service status: systemctl status j4ne"
    echo "  View logs: journalctl -u j4ne -f"
    echo "  Check logs since last restart: journalctl -u j4ne --since '5 minutes ago'"
}

# Run deployment
main "$@"
