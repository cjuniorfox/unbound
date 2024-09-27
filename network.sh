#!/bin/bash
LAN=br0
GUEST=vlan3
IP_POD="$(cat kubernetes/pod.yaml | grep ip: | awk '{print $2}')"
FORWARD="forward-port=port=53:proto=udp:toport=53:toaddr=${IP_POD} --zone=internal"

#The firewall-cmd forward rule forwards any request targeting the gateway the podman container, don't matter what host is. If you prefer just sharing the port with the network. Just comment out the firewall-cmd rules below
echo -e "Creating Firewall rule with the following command:\n  firewall-cmd --add-${FORWARD}"
firewall-cmd --remove-${FORWARD}
firewall-cmd --add-${FORWARD}
firewall-cmd --runtime-to-permanent
