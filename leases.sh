#!/bin/bash
docker compose exec dhcpd ash -c "cat /dhcpd/dhcpd.leases" | less
