FROM alpine:3.21

# Install unbound and other dependencies
RUN apk add --update bind-tools openssl py-daemonize python3 supervisor unbound  wget && \
    rm -rf /var/cache/apk/* && \
    mkdir -p /etc/unbound/unbound.conf.d && \
    mkdir -p /scripts && \
    pip3 install --no-cache-dir watchdog

ENV DOMAIN="home"

VOLUME "/unbound-conf/"

RUN echo -e 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"\ninclude-toplevel: "/unbound-conf/*.conf"' > /etc/unbound/unbound.conf

COPY etc/supervisord.conf /etc/supervisord.conf
COPY etc/unbound/unbound.conf.d/* /etc/unbound/unbound.conf.d/

COPY setup.sh /setup.sh
COPY healthcheck.sh /scripts/healthcheck.sh

COPY scripts/ad-blocking.sh /scripts/ad-blocking.sh

COPY scripts/unbound_watcher.sh /scripts/unbound_watcher.sh
COPY scripts/ipv6_watcher.sh /scripts/ipv6_watcher.sh
COPY dhcp_watcher/unbound_dhcpd_watcher.py /dhcp_watcher/unbound_dhcpd_watcher.py
COPY dhcp_watcher/unbound_dnsmasq_watcher.py /dhcp_watcher/unbound_dnsmasq_watcher.py
COPY dhcp_watcher/unbound_kea_watcher.py /dhcp_watcher/unbound_kea_watcher.py
COPY dhcp_watcher/unbound_systemd_networkd_watcher.py /dhcp_watcher/unbound_systemd_networkd_watcher.py
COPY dhcp_watcher/slaac_resolver_watcher.py /dhcp_watcher/slaac_resolver_watcher.py
RUN /setup.sh

EXPOSE 53/UDP
EXPOSE 853/UDP

ENV DHCP_LOG_LEVEL=INFO

RUN chmod +x /scripts/healthcheck.sh

HEALTHCHECK --start-period=60s --interval=120s --timeout=10s CMD ["ash", "-c", "/scripts/healthcheck.sh"]

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
