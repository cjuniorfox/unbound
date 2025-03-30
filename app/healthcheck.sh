#/bin/ash
dig @127.0.0.1 google.com | grep "status: NOERROR" || exit 1