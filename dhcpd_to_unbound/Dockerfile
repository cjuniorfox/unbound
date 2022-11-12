FROM python:alpine
RUN apk add inotify-tools
#RUN wget https://raw.githubusercontent.com/bceverly/dhcpd_to_unbound/main/dhcpd_to_unbound.py -O /dhcpd_to_unbound.py
#Temporary, until submitted pull request been accepted
RUN wget https://raw.githubusercontent.com/cjuniorfox/dhcpd_to_unbound/patch-1/dhcpd_to_unbound.py -O /dhcpd_to_unbound.py
ADD ["entrypoint.sh","/"]
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
