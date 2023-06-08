#!/bin/ash
unbound-checkconf && \
	supervisorctl -c /etc/supervisord.conf -i restart unbound || \
	echo "Unbound conf has errors and needis to be fixed."
