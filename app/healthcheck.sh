#/bin/ash
PORT=$1
if [[ -z "$PORT" ]];
	PORT=53
fi
dig @localhost -p $PORT google.com | grep "status: NOERROR" || exit 1
