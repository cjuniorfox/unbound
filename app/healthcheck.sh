#!/bin/ash
PORT=$1
PORT="${PORT:-53}"
dig @localhost -p "$PORT" google.com | grep "status: NOERROR" > /dev/null || exit 1
