#!/bin/ash
set -e

echo "[entrypoint] Running setup..."
/setup.sh

echo "[entrypoint] Starting supervisord..."
exec supervisord -c /etc/supervisord.conf
