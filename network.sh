#!/bin/bash
ZONE='internal'
## Get current rule being applyed
CONTAINER='unbound-server'
FORWARD=$(firewall-cmd --list-forward-ports --zone=internal | grep toport=53:)
echo "The firewall rule '${FORWARD}' will be removed"
firewall-cmd --remove-forward-port=${FORWARD} --zone ${ZONE}

#Retrieve unbound's current ip address.
IP_POD=$(podman inspect ${CONTAINER} --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')

echo "The container ${CONTAINER} has the IP address: ${IP_POD}"

FORWARD="forward-port=port=53:proto=udp:toport=53:toaddr=${IP_POD} --zone=${ZONE}"

#The firewall-cmd forward rule forwards any request targeting the gateway the podman container, don't matter what host is. If you prefer just sharing the port with the network. Just comment out the firewall-cmd rules below
echo -e "Creating Firewall rule with the following command:\n  firewall-cmd --add-${FORWARD}"
firewall-cmd --add-${FORWARD}
