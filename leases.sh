#!/bin/bash
docker compose exec dhcpd bash -c "cat /data/dhcpd.leases" | less
