#!/bin/ash
if [ -z "$DOMAIN" ]; then
	DOMAIN=local;
fi
WATCHER="/usr/local/sbin/unbound_watcher.py"

if [ "${DHCPSERVER}" == "dnsmasq" ]; then
	WATCHER="/usr/local/sbin/unbound_dnsmasq_watcher.py"
elif [ "${DHCPSERVER}" == "kea" ]; then
	WATCHER="/usr/local/sbin/unbound_kea_watcher.py"
fi

if [ ! -f '/dhcp.leases' ]; then
	echo "Leases file /dhcp.leases not found. Exiting..."
	exit 1
fi

python3 ${WATCHER} \
	--foreground --source /dhcp.leases \
	--target /etc/unbound/unbound.conf.d/dhcpleases.conf \
	--domain $DOMAIN \
	--log-level ${DHCP_LOG_LEVEL}
