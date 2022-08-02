#!/bin/sh
echo "server:" > /etc/unbound/unbound.conf.d/ads.conf

curl -s -o - "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts" | grep -v '^0\.0\.0\.0 0\.0\.0\.0' | grep '^0\.0\.0\.0' | awk '{print "local-zone: \""$2"\" inform_redirect\nlocal-data: \""$2" A 0.0.0.0\""}' >> /etc/unbound/unbound.conf.d/ads.conf
