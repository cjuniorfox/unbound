#!/bin/ash
set -e

# Default port
PORT="${PORT:-53}"
TLS_PORT="${TLS_PORT:-853}"

# Conf
TEMPLATE="/template-conf/unbound.conf.template"
CONF="/etc/unbound/unbound.conf.d/unbound.conf"

TLS_DIR="/etc/unbound/ssl"
TLS_SERVICE_PEM="${TLS_SERVICE_PEM:-$TLS_DIR/unbound_tls.crt}"
TLS_SERVICE_KEY="${TLS_SERVICE_KEY:-$TLS_DIR/unbound_tls.key}"

# Generate cert if not provided
if [ ! -f "$TLS_SERVICE_PEM" ] || [ ! -f "$TLS_SERVICE_KEY" ]; then
  echo "[INFO] TLS cert/key not provided, generating self-signed cert..."
  mkdir -p "$TLS_DIR"
  openssl req -x509 -newkey rsa:2048 -sha256 -nodes \
    -keyout "$TLS_SERVICE_KEY" \
    -out "$TLS_SERVICE_PEM" \
    -days 365 \
    -subj "/CN=unbound"
else
  echo "[INFO] Using provided TLS cert: $TLS_SERVICE_PEM"
  echo "[INFO] Using provided TLS key: $TLS_SERVICE_KEY"
fi


# Process template configs
sed -e "s|{PORT}|${PORT}|g" \
    -e "s|{TLS_PORT}|${TLS_PORT}|g" \
    -e "s|{TLS_SERVICE_PEM}|${TLS_SERVICE_PEM}|g" \
    -e "s|{TLS_SERVICE_KEY}|${TLS_SERVICE_KEY}|g" \
    "$TEMPLATE" > "$CONF"

# Setup control certificates
unbound-control-setup

# Download OPNsense helper scripts
mkdir -p /usr/local/opnsense/site-python/watchers
cd /usr/local/opnsense/site-python/

for i in __init__.py daemonize.LICENSE daemonize.py duckdb_helper.py log_helper.py params.py sqlite3_helper.py; do 
  wget -q "https://raw.githubusercontent.com/opnsense/core/master/src/opnsense/site-python/$i"
done

cd watchers/
for i in __init__.py dhcpd.py; do 
  wget -q "https://raw.githubusercontent.com/opnsense/core/master/src/opnsense/site-python/watchers/$i"
done

echo "[INFO] Setup complete."