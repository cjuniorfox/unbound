#!/bin/ash
dhcpd_config_file=$1
dhcpd_leases_file=$2
dhcpd_configs=$3
if [[ -z "$dhcpd_config_file" ]]; then
	echo -e "Please, declare your config file after command.\nUsage start_dhcpd.sh /tmp/dhcpd.conf /dhcpd/dhcpd.leases"
	exit 1
fi
if [[ -z "$dhcpd_leases_file" ]]; then
	echo -e "Please, declare your lease file after command.\nUsage start_dhcpd.sh /tmp/dhcpd.conf /dhcpd/dhcpd.leases"
	exit 1 
fi
if [[ -z "$DOMAIN" ]]; then
	DOMAIN="local"
fi
if [[ -z "$SUBNET" ]]; then
	SUBNET="192.168.0.0"
fi
if [[ -z "$RANGE" ]]; then
	RANGE="192.168.0.2 192.168.0.254"
fi
if [[ -z "$NETMASK" ]]; then
	NETMASK="255.255.255.0"
fi
if [[ -z "$DEFAULT_LEASE" ]]; then
	DEFAULT_LEASE="600"
fi
if [[ -z "$MAX_LEASE" ]]; then
	MAX_LEASE="3600"
fi

cat << EOF > $dhcpd_config_file
subnet $SUBNET netmask $NETMASK {
  range $RANGE;
  authoritative;
  default-lease-time $DEFAULT_LEASE;
  max-lease-time $MAX_LEASE;
  ddns-update-style none;
EOF

if [[ ! -z "$DNS" ]]; then
	cat << EOF >> $dhcpd_config_file
  option domain-name-servers $DNS;
EOF
fi

if [[ ! -z "$ROUTERS" ]]; then
	cat << EOF >> $dhcpd_config_file
  option routers $ROUTERS;
EOF
fi
cat << EOF >> $dhcpd_config_file
  option domain-name "$DOMAIN";
}
$OTHER_SETTINGS
EOF
if [[ ! -z "$dhcpd_configs" ]]; then
	for file in "$dhcpd_configs"/*.conf; do
		cat $file >> $dhcpd_config_file;
	done;
fi
cat $dhcpd_config_file
echo -e "\nStarting DHCPd server\n"
dhcpd -cf $dhcpd_config_file -f -d --no-pid -lf $dhcpd_leases_file -user dhcpd -group dhcpd $IFNAME
