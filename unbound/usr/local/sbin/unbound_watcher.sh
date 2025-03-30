#!/bin/ash
if [ -z "$DOMAIN" ]; then
	DOMAIN=lan;
fi
WATCHER="/usr/local/sbin/unbound_watcher.py"

if [ ! -z "$DHCPSERVER" ]; then
	echo "No DHCP server defined. Keeping the process running but doing nothing..."
    while true; do
        sleep 3600  # Sleep for 1 hour to keep the process alive
elif [ "${DHCPSERVER}" == "dhcpd" ]; then
	WATCHER="/usr/local/sbin/unbound_dhcpd_watcher.py"
elif [ "${DHCPSERVER}" == "dnsmasq" ]; then
	WATCHER="/usr/local/sbin/unbound_dnsmasq_watcher.py"
elif [ "${DHCPSERVER}" == "kea" ]; then
	WATCHER="/usr/local/sbin/unbound_kea_watcher.py"
fi

if [ ! -e '/dhcp.leases' ]; then
	echo "Leases file /dhcp.leases not found. Exiting..."
	exit 1
fi

python3 ${WATCHER} \
	--foreground --source /dhcp.leases \
	--target /etc/unbound/unbound.conf.d/dhcpleases.conf \
	--domain $DOMAIN \
	--log-level ${DHCP_LOG_LEVEL}
