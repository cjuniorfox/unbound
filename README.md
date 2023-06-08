DHCP Server:
https://github.com/networkboot/docker-dhcpd

Setting up the DHCP server environment variables:
DOMAIN=juniorfox.net       #Default is "local"
ROUTERS="10.1.1.61"        #Default not declared, not mandatory 
DNS="10.1.1.61"            #Default not declared, not mandatory
NETMASK="255.255.255.192"  #Defaults to 255.255.255.0
RANGE="10.1.1.1 10.1.1.58" #Defaults 192.168.0.2 192.168.0.254
SUBNET=10.1.1.0            #Defaults 192.168.0.0
DEFAULT_LEASE=43200        #Default 600
MAX_LEASE=86400            #Default 3600
OTHER_SETTINGS=            #dhcpd.conf sections accordingly to https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/networking_guide/sec-dhcp-configuring-server
