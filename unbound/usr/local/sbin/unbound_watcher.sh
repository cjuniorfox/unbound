#!/bin/ash
if [ -z "$DOMAIN" ]; then
	DOMAIN=local;
fi
python3 /usr/local/sbin/unbound_watcher.py \
	--foreground --source /dhcpd/dhcpd.leases \
	--target /etc/unbound/unbound.conf.d/dhcpleases.conf \
	--domain $DOMAIN
