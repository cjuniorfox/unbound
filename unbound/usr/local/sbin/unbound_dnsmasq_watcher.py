import os
import sys
import time
import ipaddress
import subprocess
import syslog
import argparse
sys.path.insert(0, "/usr/local/opnsense/site-python")
from daemonize import Daemonize

DNSMASQ_LEASES_FILE = '/var/lib/dnsmasq/dnsmasq.leases'
DEFAULT_DOMAIN = 'local'
CLEANUP_INTERVAL = 60  # seconds

class UnboundLocalData:
    def __init__(self):
        self.data = {}

    def is_equal(self, address, fqdn):
        return self.data.get(address) == fqdn

    def add_address(self, address, fqdn):
        self.data[address] = fqdn

    def cleanup(self, address, fqdn):
        if address in self.data:
            del self.data[address]

def unbound_control(commands, input=None):
    """ Execute unbound-control command """
    input_string = None
    if input:
        input_string = '\n'.join(input) + '\n'
    subprocess.run(['/usr/sbin/unbound-control'] + commands, input=input_string, text=True)

def parse_dnsmasq_leases(leases_file):
    leases = []
    if os.path.isfile(leases_file):
        with open(leases_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    lease = {
                        'expires': int(parts[0]),
                        'mac': parts[1],
                        'address': parts[2],
                        'hostname': parts[3],
                        'client-id': parts[4] if len(parts) > 4 else None
                    }
                    leases.append(lease)
    return leases

def run_watcher(target_filename, default_domain, watch_file):
    unbound_local_data = UnboundLocalData()
    cached_leases = {}
    last_cleanup = time.time()

    while True:
        leases = parse_dnsmasq_leases(watch_file)
        dhcpd_changed = False
        remove_rr = []
        add_rr = []

        # Process leases
        for lease in leases:
            if lease['expires'] > time.time() and lease['hostname'] and lease['address']:
                address = ipaddress.ip_address(lease['address'])
                fqdn = f"{lease['hostname']}.{default_domain}"

                # Cache the lease
                cached_leases[lease['address']] = lease
                dhcpd_changed = True

                # Update Unbound if necessary
                if not unbound_local_data.is_equal(lease['address'], fqdn):
                    remove_rr.append(f"{address.reverse_pointer}")
                    remove_rr.append(f"{fqdn}")
                    unbound_local_data.cleanup(lease['address'], fqdn)
                    add_rr.append(f"{address.reverse_pointer} PTR {fqdn}")
                    add_rr.append(f"{fqdn} IN A {lease['address']}")
                    unbound_local_data.add_address(lease['address'], fqdn)

        # Cleanup expired leases
        if time.time() - last_cleanup > CLEANUP_INTERVAL:
            last_cleanup = time.time()
            for address in list(cached_leases):
                if cached_leases[address]['expires'] < time.time():
                    fqdn = f"{cached_leases[address]['hostname']}.{default_domain}"
                    remove_rr.append(f"{ipaddress.ip_address(address).reverse_pointer}")
                    remove_rr.append(f"{fqdn}")
                    unbound_local_data.cleanup(address, fqdn)
                    del cached_leases[address]
                    dhcpd_changed = True

        # Apply changes to Unbound
        if dhcpd_changed:
            if remove_rr:
                unbound_control(['local_datas_remove'], input=remove_rr)
            if add_rr:
                unbound_control(['local_datas'], input=add_rr)

        # Sleep before next check
        time.sleep(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', help='pid file location', default='/var/run/unbound_dnsmasq_watcher.pid')
    parser.add_argument('--source', help='source leases file', default=DNSMASQ_LEASES_FILE)
    parser.add_argument('--target', help='target config file, used when unbound restarts', default='/var/unbound/dhcpleases.conf')
    parser.add_argument('--domain', help='default domain to use', default=DEFAULT_DOMAIN)
    parser.add_argument('--foreground', help='run in foreground', default=False, action='store_true')
    parser.add_argument('--log-level', help='set the logging level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    inputargs = parser.parse_args()

    syslog.openlog('unbound_dnsmasq_watcher', facility=syslog.LOG_LOCAL4)

    if inputargs.foreground:
        run_watcher(target_filename=inputargs.target, default_domain=inputargs.domain, watch_file=inputargs.source)
    else:
        syslog.syslog(syslog.LOG_NOTICE, 'daemonize unbound dnsmasq watcher.')
        cmd = lambda: run_watcher(target_filename=inputargs.target, default_domain=inputargs.domain, watch_file=inputargs.source)
        daemon = Daemonize(app="unbound_dnsmasq_watcher", pid=inputargs.pid, action=cmd)
        daemon.start()