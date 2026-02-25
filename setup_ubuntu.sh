#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Real Estate CRM — Ubuntu Setup Script
# Sets up Frappe Bench + ERPNext v15 + installs the real_estate_crm app.
#
# Usage:
#   chmod +x setup_ubuntu.sh
#   ./setup_ubuntu.sh
#
# Prerequisites:
#   - Ubuntu 22.04 or 24.04 (fresh or existing)
#   - Run as a regular user (NOT root) — script uses sudo where needed
#   - Internet connection
#
# What this script does:
#   1. Installs system dependencies (MariaDB, Redis, Node.js, wkhtmltopdf, etc.)
#   2. Configures MariaDB for Frappe
#   3. Installs Frappe Bench CLI
#   4. Creates a new bench with Frappe v15 + ERPNext v15
#   5. Creates a site and installs the real_estate_crm app
#   6. Starts the development server
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
# Change these if needed:

SITE_NAME="recrm.localhost"
BENCH_DIR="$HOME/frappe-bench"
FRAPPE_BRANCH="version-15"
ERPNEXT_BRANCH="version-15"
PYTHON_VERSION="python3"

# MariaDB root password — you'll be prompted if not set here
DB_ROOT_PASSWORD=""

# ── Colors ───────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
info() { echo -e "${CYAN}[i]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Pre-flight checks ───────────────────────────────────────────────────────

if [ "$(id -u)" -eq 0 ]; then
    err "Do NOT run this script as root. Run as a regular user — it uses sudo internally."
fi

if ! grep -qiE 'ubuntu|debian' /etc/os-release 2>/dev/null; then
    warn "This script is tested on Ubuntu 22.04/24.04. Your OS may need adjustments."
fi

# ── Step 1: System Dependencies ─────────────────────────────────────────────

info "Step 1/7 — Installing system dependencies..."

sudo apt-get update -qq

sudo apt-get install -y -qq \
    git \
    python3-dev python3-pip python3-venv python3-setuptools \
    redis-server \
    mariadb-server mariadb-client libmysqlclient-dev \
    nodejs npm \
    xvfb libfontconfig wkhtmltopdf \
    curl wget \
    supervisor \
    libssl-dev libffi-dev \
    cron \
    > /dev/null 2>&1

# Install yarn globally
sudo npm install -g yarn > /dev/null 2>&1

log "System dependencies installed."

# ── Step 2: Configure MariaDB ───────────────────────────────────────────────

info "Step 2/7 — Configuring MariaDB..."

# Add Frappe-required config
MARIADB_CONF="/etc/mysql/mariadb.conf.d/99-frappe.cnf"
if [ ! -f "$MARIADB_CONF" ]; then
    sudo tee "$MARIADB_CONF" > /dev/null <<'MYCNF'
[mysqld]
character-set-server  = utf8mb4
collation-server      = utf8mb4_unicode_ci

[mysql]
default-character-set  = utf8mb4
MYCNF
    sudo systemctl restart mariadb
    log "MariaDB configured with utf8mb4."
else
    log "MariaDB config already exists — skipping."
fi

# Prompt for DB root password if not set
if [ -z "$DB_ROOT_PASSWORD" ]; then
    echo ""
    echo -e "${CYAN}Enter your MariaDB root password${NC}"
    echo "(If you haven't set one yet, just press Enter for blank, then run"
    echo " sudo mysql_secure_installation afterwards)"
    echo ""
    read -sp "MariaDB root password: " DB_ROOT_PASSWORD
    echo ""
fi

# Test DB connection
if mysql -u root -p"$DB_ROOT_PASSWORD" -e "SELECT 1;" > /dev/null 2>&1; then
    log "MariaDB connection verified."
else
    # Try without password (fresh install)
    if sudo mysql -e "SELECT 1;" > /dev/null 2>&1; then
        warn "MariaDB has no root password set. Setting it now..."
        sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$DB_ROOT_PASSWORD';"
        sudo mysql -e "FLUSH PRIVILEGES;"
        log "MariaDB root password set."
    else
        err "Cannot connect to MariaDB. Check your root password and try again."
    fi
fi

# ── Step 3: Install Frappe Bench CLI ────────────────────────────────────────

info "Step 3/7 — Installing Frappe Bench CLI..."

if command -v bench &> /dev/null; then
    log "Bench CLI already installed: $(bench --version 2>/dev/null || echo 'unknown version')"
else
    pip3 install --user frappe-bench > /dev/null 2>&1

    # Ensure ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        export PATH="$HOME/.local/bin:$PATH"
    fi

    log "Bench CLI installed."
fi

# ── Step 4: Initialize Bench ────────────────────────────────────────────────

info "Step 4/7 — Setting up Frappe Bench at $BENCH_DIR ..."

if [ -d "$BENCH_DIR" ]; then
    warn "Bench directory already exists at $BENCH_DIR — using existing bench."
    cd "$BENCH_DIR"
else
    bench init --frappe-branch "$FRAPPE_BRANCH" "$BENCH_DIR"
    cd "$BENCH_DIR"
    log "Bench initialized."
fi

# ── Step 5: Install ERPNext ─────────────────────────────────────────────────

info "Step 5/7 — Installing ERPNext..."

if [ -d "$BENCH_DIR/apps/erpnext" ]; then
    log "ERPNext already present — skipping download."
else
    bench get-app --branch "$ERPNEXT_BRANCH" erpnext
    log "ERPNext downloaded."
fi

# ── Step 6: Create Site + Install Apps ──────────────────────────────────────

info "Step 6/7 — Creating site '$SITE_NAME' and installing apps..."

if [ -d "$BENCH_DIR/sites/$SITE_NAME" ]; then
    warn "Site '$SITE_NAME' already exists — skipping site creation."
else
    bench new-site "$SITE_NAME" \
        --mariadb-root-password "$DB_ROOT_PASSWORD" \
        --admin-password admin
    log "Site created. Admin password: admin"
fi

# Install ERPNext on the site
bench --site "$SITE_NAME" install-app erpnext 2>/dev/null || warn "ERPNext may already be installed on this site."

# Set as default site so bench commands target it
bench use "$SITE_NAME"

log "ERPNext installed on $SITE_NAME."

# ── Step 7: Install Real Estate CRM ────────────────────────────────────────

info "Step 7/7 — Installing Real Estate CRM app..."

# Find the app source — look relative to the script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SOURCE=""

# Check common locations
if [ -d "$SCRIPT_DIR/real_estate_crm" ]; then
    APP_SOURCE="$SCRIPT_DIR/real_estate_crm"
elif [ -d "$SCRIPT_DIR/../real_estate_crm" ]; then
    APP_SOURCE="$(cd "$SCRIPT_DIR/../real_estate_crm" && pwd)"
fi

if [ -d "$BENCH_DIR/apps/real_estate_crm" ]; then
    warn "real_estate_crm already in bench apps — running migrate only."
else
    if [ -n "$APP_SOURCE" ] && [ -d "$APP_SOURCE" ]; then
        info "Found app at: $APP_SOURCE"
        bench get-app "$APP_SOURCE"
    else
        echo ""
        echo -e "${YELLOW}Could not auto-detect the real_estate_crm app location.${NC}"
        echo "Please provide the path to the real_estate_crm folder"
        echo "(the folder containing setup.py), or a git URL:"
        echo ""
        read -rp "Path or Git URL: " USER_APP_PATH

        if [ -z "$USER_APP_PATH" ]; then
            err "No path provided. Exiting."
        fi
        bench get-app "$USER_APP_PATH"
    fi
fi

bench --site "$SITE_NAME" install-app real_estate_crm 2>/dev/null || true
bench --site "$SITE_NAME" migrate
bench build

log "Real Estate CRM installed and migrated."

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Site:      ${CYAN}$SITE_NAME${NC}"
echo -e "  Bench:     ${CYAN}$BENCH_DIR${NC}"
echo -e "  Login:     ${CYAN}Administrator / admin${NC}"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo ""
echo "  1. Start the server:"
echo -e "     ${CYAN}cd $BENCH_DIR && bench start${NC}"
echo ""
echo "  2. Open in browser:"
echo -e "     ${CYAN}http://$SITE_NAME:8000${NC}"
echo ""
echo "  3. Complete the Setup Wizard (set Company name, currency, etc.)"
echo ""
echo "  4. If Chart of Accounts didn't get created (no company at install time):"
echo -e "     ${CYAN}bench --site $SITE_NAME execute real_estate_crm.install.create_chart_of_accounts${NC}"
echo ""
echo "  5. Go to the 'Real Estate' workspace — all modules are ready."
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
