FROM alpine:edge
#RUN apk add --no-cache --upgrade && apk add ca-certificates unbound netcat-openbsd

# Install unbound
RUN echo "http://dl-4.alpinelinux.org/alpine/latest-stable/main/" >> /etc/apk/repositories && \
    apk add --update unbound bind-tools supervisor && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/*

RUN mkdir /etc/unbound/unbound.conf.d/
RUN echo 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"' > /etc/unbound/unbound.conf
ADD ["supervisord.conf","/etc/supervisord.conf"]
ADD ["unbound.conf","/etc/unbound/unbound.conf.d/unbound.conf"]
ADD ["ad-blocking.sh","/usr/local/sbin/ad-blocking.sh"]
RUN chmod 770 /usr/local/sbin/ad-blocking.sh
HEALTHCHECK --start-period=10s --interval=120s --timeout=10s CMD nc -z -v -u 127.0.0.1 53 >/dev/null 2>&1 || exit 1
ENTRYPOINT ["supervisord", "-c", "/etc/supervisord.conf"]
