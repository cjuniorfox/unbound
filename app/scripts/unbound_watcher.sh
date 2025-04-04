#!/bin/ash
if [ -z "$DOMAIN" ]; then
	DOMAIN=home;
fi

if [ -z "$DHCPSERVER" ]; then
	echo "No DHCP server defined. Keeping the process running but doing nothing..."
    while true; do
        sleep 3600  # Sleep for 1 hour to keep the process alive
	done
elif [ "${DHCPSERVER}" == "dhcpd" ]; then
	WATCHER="/dhcp_watcher/unbound_dhcpd_watcher.py"
elif [ "${DHCPSERVER}" == "dnsmasq" ]; then
	WATCHER="/dhcp_watcher/unbound_dnsmasq_watcher.py"
elif [ "${DHCPSERVER}" == "kea" ]; then
	WATCHER="/dhcp_watcher/unbound_kea_watcher.py"
elif [ "${DHCPSERVER}" == "systemd-networkd" ]; then
	WATCHER="/dhcp_watcher/unbound_systemd_networkd_watcher.py"
else
	echo "Unknown DHCP server type: ${DHCPSERVER}. Exiting..."
	exit 1
fi


if [ ! -e '/dhcp.leases' ]; then
	echo "Leases file or folder /dhcp.leases not found. Exiting..."
	exit 1
fi

python3 ${WATCHER} \
	--foreground --source /dhcp.leases \
	--target /etc/unbound/unbound.conf.d/dhcpleases.conf \
	--domain $DOMAIN \
	--log-level ${DHCP_LOG_LEVEL}
