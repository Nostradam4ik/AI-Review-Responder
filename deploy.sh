#!/bin/bash
set -e

DOMAIN=${1:-"your-domain.com"}
EMAIL=${2:-"your-email@example.com"}

echo "==> Deploying AI Review Responder to $DOMAIN"

# 1. Pull latest code
git pull origin main

# 2. Create .env.prod from .env if it doesn't exist
if [ ! -f .env.prod ]; then
  echo "ERROR: .env.prod not found. Copy .env.example to .env.prod and fill in values."
  exit 1
fi

# 3. Build and start services (without nginx first for certbot)
docker compose -f docker-compose.prod.yml up -d postgres backend frontend

# 4. Obtain SSL certificate (first time only)
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  echo "==> Obtaining SSL certificate for $DOMAIN"
  docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot -w /var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"
fi

# 5. Start nginx
docker compose -f docker-compose.prod.yml up -d nginx certbot

echo "==> Deployment complete! App running at https://$DOMAIN"
