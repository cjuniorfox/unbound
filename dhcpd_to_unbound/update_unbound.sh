#!/bin/ash
echo "Updating ${DYNAMIC_CONF} using ${DHCPD_LEASES}" 
python3 /dhcpd_to_unbound.py --input "${DHCPD_LEASES}" --domain "${LOCALDOMAIN}" > "${DYNAMIC_CONF}"
