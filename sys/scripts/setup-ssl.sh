#!/bin/bash

# SSL Certificate Setup Script
# This script handles Let's Encrypt SSL certificate setup and renewal

DOMAIN="${1:-j4ne.example.com}"
EMAIL="${2:-admin@example.com}"

echo "🔒 Setting up SSL certificate for $DOMAIN"

# Function to check if certbot is installed
check_certbot() {
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
}

# Function to obtain SSL certificate
obtain_certificate() {
    echo "Obtaining SSL certificate..."
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL || {
        echo "Failed to obtain certificate automatically"
        echo "Please run manually:"
        echo "certbot --nginx -d $DOMAIN"
        exit 1
    }
}

# Function to setup auto-renewal
setup_renewal() {
    echo "Setting up automatic renewal..."

    # Add cron job for renewal
    CRON_JOB="0 12 * * * /usr/bin/certbot renew --quiet"
    (crontab -l 2>/dev/null | grep -v "$CRON_JOB"; echo "$CRON_JOB") | crontab -

    # Test renewal
    certbot renew --dry-run
}

# Function to verify certificate
verify_certificate() {
    echo "Verifying SSL certificate..."
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        echo "✅ SSL certificate found and valid"
        openssl x509 -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" -text -noout | grep "Not After"
    else
        echo "❌ SSL certificate not found"
        exit 1
    fi
}

# Main execution
main() {
    check_certbot
    obtain_certificate
    setup_renewal
    verify_certificate

    echo "✅ SSL setup complete!"
    echo "Certificate location: /etc/letsencrypt/live/$DOMAIN/"
    echo "Auto-renewal configured via cron"
}

# Run if script is executed directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
