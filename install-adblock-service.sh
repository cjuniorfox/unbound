#!/bin/bash
cp unbound-ad-blocking.service /etc/systemd/system/
cp unbound-ad-blocking.timer /etc/systemd/system/
systemctl daemon-reload
