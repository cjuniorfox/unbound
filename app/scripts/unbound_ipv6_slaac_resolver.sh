#!/bin/ash
if [ -z "$DOMAIN" ]; then
	DOMAIN=home;
fi

if [ -z "$SLAAC_RESOLVER" ]; then
	echo "No SLAAC Watcher defined. Keeping the process running but doing nothing..."
    while true; do
        sleep 3600  # Sleep for 1 hour to keep the process alive
	done
elif [ "${SLAAC_RESOLVER}" == "slaac-resolver" ]; then
	WATCHER="/dhcp_watcher/unbound_slaac_resolver_watcher.py"
else
	echo "Unknown SLAAC Watcher type: ${SLAAC_RESOLVER}. Exiting..."
	exit 1
fi


if [ ! -e '/slaac-resolver' ]; then
	echo "slaac-resolver directory not found. Exiting..."
	exit 1
fi

python3 ${WATCHER} \
	--foreground --source /slaac-resolver \
	--domain $DOMAIN \
	--log-level ${DHCP_LOG_LEVEL}
