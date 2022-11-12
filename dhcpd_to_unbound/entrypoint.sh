#!/bin/ash
DYNAMIC_CONF="/unbound.conf.d/dhcpd.conf"
echo "Starting DHCPD to Unbound"
echo "DHCP lease: ${DHCPD_LEASES}"
echo "Localdomain: ${LOCALDOMAIN}"
while inotifywait -e modify "${DHCPD_LEASES}"; do
  echo "Updating ${DYNAMIC_CONF}"
  python3 /dhcpd_to_unbound.py --input "${DHCPD_LEASES}" --domain "${LOCALDOMAIN}" > "${DYNAMIC_CONF}"
done;
