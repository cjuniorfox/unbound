FROM alpine:3.18
#RUN apk add --no-cache --upgrade && apk add ca-certificates unbound netcat-openbsd

# Install unbound
RUN echo "http://dl-4.alpinelinux.org/alpine/latest-stable/main/" >> /etc/apk/repositories && \
    apk add --update wget unbound openssl python3 bind-tools supervisor && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/*

RUN mkdir /etc/unbound/unbound.conf.d/
RUN echo 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"' > /etc/unbound/unbound.conf
ADD ["etc/supervisord.conf","/etc/supervisord.conf"]
ADD ["etc/unbound/unbound.conf.d/*","/etc/unbound/unbound.conf.d/"]
ADD ["usr/local/sbin/ad-blocking.sh","/usr/local/sbin/ad-blocking.sh"]
ADD ["setup.sh","/setup.sh"]
ADD ["usr/local/sbin/ad-blocking.sh","/usr/local/sbin/ad-blocking.sh"]
ADD ["usr/local/sbin/unbound_watcher.sh","/usr/local/sbin/unbound_watcher.sh"]
ADD ["usr/local/sbin/unbound_watcher.py","/usr/local/sbin/unbound_watcher.py"]
RUN chmod 770 /setup.sh /usr/local/sbin/ad-blocking.sh /usr/local/sbin/unbound_watcher.sh /usr/local/sbin/unbound_watcher.py
RUN /setup.sh
HEALTHCHECK --start-period=10s --interval=120s --timeout=10s CMD nc -z -v -u 127.0.0.1 53 >/dev/null 2>&1 || exit 1
ENTRYPOINT ["supervisord", "-c", "/etc/supervisord.conf"]
