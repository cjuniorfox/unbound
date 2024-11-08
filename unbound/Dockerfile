FROM alpine:3.18

# Install unbound and other dependencies
RUN apk add --update bind-tools openssl python3 supervisor unbound wget && \
    rm -rf /var/cache/apk/* && \
    mkdir -p /etc/unbound/unbound.conf.d/

# Define volumes
VOLUME /etc/certificates
VOLUME /unbound-conf
VOLUME /etc/unbound/unbound.conf.d/
VOLUME /dhcp.leases

ENV DOMAIN="local"
ENV DHCPSERVER="dhcpd"

# Configure unbound
RUN echo -e 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"\ninclude-toplevel: "/unbound-conf/*.conf"' > /etc/unbound/unbound.conf

# Copy configuration and scripts
COPY etc/supervisord.conf /etc/supervisord.conf
COPY etc/unbound/unbound.conf.d/* /etc/unbound/unbound.conf.d/
COPY usr/local/sbin/ad-blocking.sh /usr/local/sbin/ad-blocking.sh
COPY setup.sh /setup.sh
COPY usr/local/sbin/unbound_watcher.sh /usr/local/sbin/unbound_watcher.sh
COPY usr/local/sbin/unbound_watcher.py /usr/local/sbin/unbound_watcher.py
COPY usr/local/sbin/unbound_dnsmasq_watcher.py /usr/local/sbin/unbound_dnsmasq_watcher.py
COPY usr/local/sbin/unbound_kea_watcher.py /usr/local/sbin/unbound_kea_watcher.py

# Run setup script
RUN /setup.sh

# Expose DNS and DNS-over-TLS ports
EXPOSE 53/UDP
EXPOSE 853/UDP

ENV DHCP_LOG_LEVEL=INFO

# Healthcheck to ensure Unbound is running correctly
HEALTHCHECK --start-period=60s --interval=120s --timeout=10s CMD dig @127.0.0.1 google.com | grep "status: NOERROR" || exit 1

# Start supervisord
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
