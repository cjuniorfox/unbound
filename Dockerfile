FROM alpine:edge
#RUN apk add --no-cache --upgrade && apk add ca-certificates unbound netcat-openbsd

# Install unbound
RUN echo "http://dl-4.alpinelinux.org/alpine/latest-stable/main/" >> /etc/apk/repositories && \
    apk add --update unbound bind-tools && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/*

RUN mkdir /etc/unbound/unbound.conf.d/
RUN echo 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"' > /etc/unbound/unbound.conf
VOLUME /etc/unbound/unbound.conf.d/
COPY unbound.conf /etc/unbound/unbound.conf.d/unbound.conf
#EXPOSE 53/tcp 
#EXPOSE 53/udp 
#EXPOSE 853/tcp
#EXPOSE 853/udp
HEALTHCHECK --start-period=10s --interval=120s --timeout=10s CMD nc -z -v -u 127.0.0.1 53 >/dev/null 2>&1 || exit 1

ENTRYPOINT ["/usr/sbin/unbound", "-c", "/etc/unbound/unbound.conf", "-dv"]
