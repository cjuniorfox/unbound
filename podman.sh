#!/bin/bash
podman volume create unbound_conf

podman run -d --name unbound --restart always \
	--env DOMAIN=$DOMAIN \
	--volume /var/lib/dhcp/:/dhcpd \
	--volume unbound_conf:/unbound-conf \
	--volume certificates:/etc/certificates/ \
	--network host docker.io/cjuniorfox/unbound
