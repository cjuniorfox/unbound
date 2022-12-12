#!/bin/ash
export DYNAMIC_CONF="/unbound.conf.d/dhcpd.conf"
echo "Starting DHCPD to Unbound"
echo "DHCP lease: ${DHCPD_LEASES}"
echo "Localdomain: ${LOCALDOMAIN}"
while :; do
	echo "Monitor started/restarted at $(date)"
	inotifyd /update_unbound.sh ${DHCPD_LEASES}:w
done;
