#!/bin/sh
echo "Downloading blacklisted domains ads list at $(date)."
while :; do
	echo "server:" > /etc/unbound/unbound.conf.d/ads.conf
	wget -q -O - "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts" | grep -v '^0\.0\.0\.0 0\.0\.0\.0' | grep '^0\.0\.0\.0' | awk '{print "local-zone: \""$2"\" inform_redirect\nlocal-data: \""$2" A 0.0.0.0\""}' >> /etc/unbound/unbound.conf.d/ads.conf
	[ $? -eq 0 ] && echo "Blacklisted domains ads list finished at $(date) Successfully." || echo "An error occurried while downloading blacklisted ads list at $(date) with error code $?."
	sleep 1d
done
