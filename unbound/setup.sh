apk add unbound openssl python3 bind-tools
echo 'include-toplevel: "/etc/unbound/unbound.conf.d/*.conf"' > /etc/unbound/unbound.conf
unbound-control-setup
ln -s /usr/bin/python3  /usr/local/bin/python3
#Downloading opensense scripts
mkdir /usr/local/opnsense/site-python/watchers -p
cd /usr/local/opnsense/site-python/
for i in __init__.py daemonize.LICENSE daemonize.py duckdb_helper.py log_helper.py params.py sqlite3_helper.py; do 
	wget "https://raw.githubusercontent.com/opnsense/core/master/src/opnsense/site-python/$i"; 
done

cd  watchers/

for i in __init__.py daemonize.LICENSE daemonize.py duckdb_helper.py log_helper.py params.py sqlite3_helper.py; do 
	wget "https://raw.githubusercontent.com/opnsense/core/master/src/opnsense/site-python/$i";
done
