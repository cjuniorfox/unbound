FROM alpine:edge
#RUN apk add --no-cache --upgrade && apk add ca-certificates unbound netcat-openbsd

# Install unbound
RUN echo "http://dl-4.alpinelinux.org/alpine/latest-stable/main/" >> /etc/apk/repositories && \
    apk add --update unbound bind-tools supervisor && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/*

RUN mkdir /etc/unbound/unbound.conf.d/
RUN echo 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"' > /etc/unbound/unbound.conf
ADD ["supervisord.conf","/etc/supervisord.conf"]
ADD ["unbound.conf.d/*","/etc/unbound/unbound.conf.d/"]
ADD ["ad-blocking.sh","/usr/local/sbin/ad-blocking.sh"]
ADD ["restart-unbound.sh","/"]
ADD ["unbound-conf-monitor.sh","/"]
RUN chmod 770 /restart-unbound.sh /usr/local/sbin/ad-blocking.sh /unbound-conf-monitor.sh
HEALTHCHECK --start-period=10s --interval=120s --timeout=10s CMD nc -z -v -u 127.0.0.1 53 >/dev/null 2>&1 || exit 1
ENTRYPOINT ["supervisord", "-c", "/etc/supervisord.conf"]
