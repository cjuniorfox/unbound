FROM alpine:3.18

# Install unbound
RUN apk add --update dhcp && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/*

VOLUME /dhcpd
ADD ["usr/local/sbin/start_dhcp_server.sh","/usr/local/sbin/start_dhcp_server.sh"]
RUN chmod 770 /usr/local/sbin/start_dhcp_server.sh
HEALTHCHECK --start-period=10s --interval=120s --timeout=10s CMD nc -zvu 127.0.0.1 67 >/dev/null 2>&1 || exit 1
ENTRYPOINT ["/usr/local/bin/start_dhcp_server.sh", "/tmp/dhcpd.conf"]
