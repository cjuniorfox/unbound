#!/bin/bash
DOMAIN='juniorfox.net'
POD='unbound-pod'
NETWORK='unbound-net'
LAN=br0
GUEST=guest
IP_LAN="$(ip -o -f inet a show ${LAN} | awk '{print $4}' | awk -F"/" '{print $1}')"
IP_GUEST="$(ip -o -f inet a show ${GUEST} | awk '{print $4}' | awk -F"/" '{print $1}')"
NET="10.89.10"
IP_POD="${NET}.100"
FORWARD="forward-port=port=53:proto=udp:toport=53:toaddr=${IP_POD} --zone=internal"

echo "Removing pod ${POD}"
podman pod stop ${POD}
podman pod rm ${POD} && podman network rm ${NETWORK}

#The firewall-cmd forward rule forwards any request targeting the gateway the podman container, don't matter what host is. If you prefer just sharing the port with the network. Just comment out the firewall-cmd rules below
echo "Creating firewall-cmd '${FORWARD}'"
firewall-cmd --permanent --remove-${FORWARD}
firewall-cmd --permanent --add-${FORWARD}
firewall-cmd --reload

echo "Creating volume and network ${NETWORK}"
podman volume create unbound_conf
podman network create ${NETWORK} \
	--driver bridge \
	--gateway ${NET}.97 \
	--subnet ${NET}.96/28 \
	--ip-range ${NET}.98/28

echo "Creating pod ${POD}"
podman pod create \
	-p ${IP_LAN}:53:53/udp \
	-p ${IP_GUEST}:53:53/udp \
	-p 853:853/tcp \
	--network ${NETWORK} \
	--ip ${IP_POD} \
	${POD}

echo "Creating container for pod ${POD}"
podman run -d \
	--pod ${POD} \
	--name ${POD}-server \
	--restart always \
	--env DOMAIN=${DOMAIN} \
	--volume /var/lib/dhcp/:/dhcpd \
	--volume unbound_conf:/unbound-conf \
	--volume certificates:/etc/certificates/ \
	cjuniorfox/unbound



