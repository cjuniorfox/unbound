#!/bin/ash
if [ -z "$DOMAIN" ]; then
	DOMAIN=local;
fi
WATCHER="/usr/local/sbin/unbound_watcher.py"

if [ "${DHCPSERVER}" == "dnsmasq" ]; then
	WATCHER="/usr/local/sbin/unbound_dnsmasq_watcher.py"
fi

python3 ${WATCHER} \
	--foreground --source /dhcp.leases \
	--target /etc/unbound/unbound.conf.d/dhcpleases.conf \
	--domain $DOMAIN
