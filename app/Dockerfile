FROM alpine:3.18

# Install unbound and other dependencies
RUN apk add --update bind-tools openssl python3 supervisor unbound wget && \
    rm -rf /var/cache/apk/* && \
    mkdir -p /etc/unbound/unbound.conf.d

ENV DOMAIN="home"
ENV DHCPSERVER="dhcpd"

VOLUME "/unbound-conf/"

RUN echo -e 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"\ninclude-toplevel: "/unbound-conf/*.conf"' > /etc/unbound/unbound.conf

COPY etc/supervisord.conf /etc/supervisord.conf
COPY etc/unbound/unbound.conf.d/* /etc/unbound/unbound.conf.d/
COPY usr/local/sbin/ad-blocking.sh /usr/local/sbin/ad-blocking.sh
COPY setup.sh /setup.sh
COPY usr/local/sbin/unbound_watcher.sh /usr/local/sbin/unbound_watcher.sh
COPY usr/local/sbin/unbound_watcher.py /usr/local/sbin/unbound_watcher.py
COPY usr/local/sbin/unbound_dnsmasq_watcher.py /usr/local/sbin/unbound_dnsmasq_watcher.py
COPY usr/local/sbin/unbound_kea_watcher.py /usr/local/sbin/unbound_kea_watcher.py

RUN /setup.sh

EXPOSE 53/UDP
EXPOSE 853/UDP

ENV DHCP_LOG_LEVEL=INFO

HEALTHCHECK --start-period=60s --interval=120s --timeout=10s CMD dig @127.0.0.1 google.com | grep "status: NOERROR" || exit 1

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
