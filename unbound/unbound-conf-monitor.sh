#!/bin/ash
echo "Starting configuration change monitor"
while :; do
	echo "Monitor started at $(date)"
	inotifyd /restart-unbound.sh /etc/unbound/unbound.conf.d/:w
done
