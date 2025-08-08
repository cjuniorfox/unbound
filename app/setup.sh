#!/bin/ash
set -e

# Default ports
PORT="${PORT:-53}"
TLS_PORT="${TLS_PORT:-853}"

mkdir -p /etc/unbound/unbound.conf.d/

# Process template configs
for conf in /template-conf/*.conf; do
  sed -e "s/{PORT}/${PORT}/g" -e "s/{TLS_PORT}/${TLS_PORT}/g" "$conf" \
    > "/etc/unbound/unbound.conf.d/$(basename "$conf")"
done

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
