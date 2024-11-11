import os
import sys
import time
import ipaddress
import subprocess
import syslog
import argparse
import csv
import logging
from datetime import timedelta
sys.path.insert(0, "/usr/local/opnsense/site-python")
from daemonize import Daemonize

KEA_LEASES_FILE = '/var/lib/kea/dhcp4.leases'
DEFAULT_DOMAIN = 'local'
CLEANUP_INTERVAL = 60  # seconds

# Set up logging
logger = logging.getLogger(__name__)

class UnboundLocalData:
    def __init__(self):
        self.data = {}

    def is_equal(self, address, fqdn):
        return self.data.get(address) == fqdn

    def add_address(self, address, fqdn):
        self.data[address] = fqdn
        logger.debug(f"Added address {address} with FQDN {fqdn} to UnboundLocalData")

    def cleanup(self, address, fqdn):
        if address in self.data:
            del self.data[address]
            logger.debug(f"Removed address {address} with FQDN {fqdn} from UnboundLocalData")

def unbound_control(commands, input=None):
    """ Execute unbound-control command """
    input_string = None
    if input:
        input_string = '\n'.join(input) + '\n'
    logger.debug(f"Executing unbound-control command: {commands}")
    result = subprocess.run(['/usr/sbin/unbound-control'] + commands, input=input_string, text=True, capture_output=True)
    logger.debug(f"unbound-control output: {result.stdout}")
    if result.stderr:
        logger.error(f"unbound-control error: {result.stderr}")

def parse_kea_leases(leases_file):
    leases = []
    if os.path.isfile(leases_file):
        with open(leases_file, 'r') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                lease = {
                    'address': row['address'],
                    'hwaddr': row['hwaddr'],
                    'hostname': row['hostname'],
                    'expire': int(row['expire']),
                }
                leases.append(lease)
        logger.debug(f"Parsed {len(leases)} leases from {leases_file}")
    else:
        logger.warning(f"Leases file not found: {leases_file}")
    return leases

def run_watcher(target_filename, default_domain, watch_file):
    logger.info(f"Starting watcher with target_filename={target_filename}, default_domain={default_domain}, watch_file={watch_file}")
    unbound_local_data = UnboundLocalData()
    cached_leases = {}
    last_cleanup = time.time()

    while True:
        logger.debug("Starting new iteration of lease processing")
        leases = parse_kea_leases(watch_file)
        dhcpd_changed = False
        remove_rr = []
        add_rr = []

        # Process leases
        for lease in leases:
            if lease['expire'] > time.time() and lease['hostname'] and lease['address']:
                address = ipaddress.ip_address(lease['address'])
                fqdn = f"{lease['hostname']}.{default_domain}"
                logger.debug(f"Processing lease: address={address}, hostname={lease['hostname']}")

                # Cache the lease
                cached_leases[lease['address']] = lease
                dhcpd_changed = True

                # Update Unbound if necessary
                if not unbound_local_data.is_equal(lease['address'], fqdn):
                    logger.info(f"Updating Unbound for {address} {lease['hostname']}.{fqdn}")
                    remove_rr.append(f"{address.reverse_pointer}")
                    remove_rr.append(f"{fqdn}")
                    unbound_local_data.cleanup(lease['address'], fqdn)
                    add_rr.append(f"{address.reverse_pointer} PTR {fqdn}")
                    add_rr.append(f"{fqdn} IN A {lease['address']}")
                    unbound_local_data.add_address(lease['address'], fqdn)
            elif lease['expire'] < time.time():
                logger.debug(f"Lease Expired: [{lease['hostname']}: {lease['address']}] by [{str(timedelta(seconds=(time.time() - lease['expire'])))}]. Expired epoch [{lease['expire']}].")
            else:
                logger.debug(f"Lease ignored: [{lease['hostname']}: {lease['address']}]. Does not have hostname or address")

        # Cleanup expired leases
        if time.time() - last_cleanup > CLEANUP_INTERVAL:
            logger.debug("Performing cleanup of expired leases")
            last_cleanup = time.time()
            for address in list(cached_leases):
                if cached_leases[address]['expire'] < time.time():
                    logger.info(f"Removing expired lease for {address}")
                    fqdn = f"{cached_leases[address]['hostname']}.{default_domain}"
                    remove_rr.append(f"{ipaddress.ip_address(address).reverse_pointer}")
                    remove_rr.append(f"{fqdn}")
                    unbound_local_data.cleanup(address, fqdn)
                    del cached_leases[address]
                    dhcpd_changed = True

        # Apply changes to Unbound
        if dhcpd_changed:
            if remove_rr:
                logger.info(f"Removing {len(remove_rr)} resource records")
                unbound_control(['local_datas_remove'], input=remove_rr)
            if add_rr:
                logger.info(f"Adding {len(add_rr)} resource records")
                unbound_control(['local_datas'], input=add_rr)
        # Sleep before next check
        time.sleep(5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', help='pid file location', default='/var/run/unbound_kea_watcher.pid')
    parser.add_argument('--source', help='source leases file', default=KEA_LEASES_FILE)
    parser.add_argument('--target', help='target config file, used when unbound restarts', default='/var/unbound/dhcpleases.conf')
    parser.add_argument('--domain', help='default domain to use', default=DEFAULT_DOMAIN)
    parser.add_argument('--foreground', help='run in foreground', default=False, action='store_true')
    parser.add_argument('--log-level', help='set the logging level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    inputargs = parser.parse_args()

    # Set the logging level based on the argument
    logging.basicConfig(level=getattr(logging, inputargs.log_level), format='%(asctime)s - %(levelname)s - %(message)s')
    syslog.openlog('unbound_kea_watcher', facility=syslog.LOG_LOCAL4)

    logger.info(f"Starting unbound_kea_watcher with arguments: {vars(inputargs)}")
    if inputargs.foreground:
        logger.info("Running in foreground mode")
        run_watcher(target_filename=inputargs.target, default_domain=inputargs.domain, watch_file=inputargs.source)
    else:
        logger.info("Running in daemon mode")
        syslog.syslog(syslog.LOG_NOTICE, 'daemonize unbound kea watcher.')
        cmd = lambda: run_watcher(target_filename=inputargs.target, default_domain=inputargs.domain, watch_file=inputargs.source)
        daemon = Daemonize(app="unbound_kea_watcher", pid=inputargs.pid, action=cmd)
        daemon.start()