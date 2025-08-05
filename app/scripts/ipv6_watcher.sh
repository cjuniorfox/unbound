#!/bin/ash
if [ -z "$DOMAIN" ]; then
	DOMAIN=home;
fi

if [ -z "$IPV6_WATCHER" ]; then
	echo "No SLAAC Watcher defined. Keeping the process running but doing nothing..."
    while true; do
        sleep 3600  # Sleep for 1 hour to keep the process alive
	done
elif [ "${IPV6_WATCHER}" == "slaac-resolver" ]; then
	WATCHER="/dhcp_watcher/slaac_resolver_watcher.py"
else
	echo "Unknown SLAAC Watcher type: ${IPV6_WATCHER}. Exiting..."
	exit 1
fi


if [ ! -e '/ipv6-watcher' ]; then
	echo "ipv6-watcher directory not found. Exiting..."
	exit 1
fi

python3 ${WATCHER} \
	--source /ipv6-watcher \
	--domain $DOMAIN \
	--log-level ${DHCP_LOG_LEVEL}
