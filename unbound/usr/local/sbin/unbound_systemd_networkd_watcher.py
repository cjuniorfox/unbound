import os
import sys
import time
import ipaddress
import subprocess
import syslog
import argparse
import logging
from datetime import timedelta
import json
from daemonize import Daemonize

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

def parse_systemd_leases(dir_or_file):
    leases = []
    if os.path.isfile(dir_or_file):  # If it's a single file
        try:
            with open(dir_or_file, 'r') as f:
                data = json.load(f)
                for lease in data.get('Leases', []):
                    leases.append({
                        'address': '.'.join(map(str, lease['Address'])),
                        'hostname': lease.get('Hostname', ''),
                        'expire': lease.get('ExpirationRealtimeUSec', 0) // 1_000_000,  # Convert microseconds to seconds
                    })
            logger.debug(f"Parsed leases from file: {dir_or_file}")
        except Exception as e:
            logger.warning(f"Failed to parse file {dir_or_file}: {e}")
    elif os.path.isdir(dir_or_file):  # If it's a directory
        for filename in os.listdir(dir_or_file):
            file_path = os.path.join(dir_or_file, filename)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        for lease in data.get('Leases', []):
                            leases.append({
                                'address': '.'.join(map(str, lease['Address'])),
                                'hostname': lease.get('Hostname', ''),
                                'expire': lease.get('ExpirationRealtimeUSec', 0) // 1_000_000,  # Convert microseconds to seconds
                            })
                    logger.debug(f"Parsed leases from file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to parse file {file_path}: {e}")
    else:
        logger.warning(f"Leases path not found: {dir_or_file}")
    return leases

def run_watcher(target_filename, default_domain, watch_dir_or_file):
    logger.info(f"Starting watcher with target_filename={target_filename}, default_domain={default_domain}, watch_directory={watch_dir_or_file}")
    unbound_local_data = UnboundLocalData()
    cached_leases = {}
    last_cleanup = time.time()

    while True:
        logger.debug("Starting new iteration of lease processing")
        leases = parse_systemd_leases(watch_dir_or_file)
        dhcpd_changed = False
        remove_rr = []
        add_rr = []
    
        # Create a set of active lease addresses
        active_addresses = {lease['address'] for lease in leases}
    
        # Process leases
        for lease in leases:
            if lease['expire'] > time.time() and lease['hostname'] and lease['address']:
                address = ipaddress.ip_address(lease['address'])
                fqdn = f"{lease['hostname']}.{default_domain}"
                logger.debug(f"Processing lease: address={address}, hostname={lease['hostname']}")
    
                # Check if the lease is new or has changed
                if lease['address'] not in cached_leases or cached_leases[lease['address']] != lease:
                    cached_leases[lease['address']] = lease
                    dhcpd_changed = True
                    logger.debug(f"Lease added/updated: {lease}")
    
                # Update Unbound if necessary
                if not unbound_local_data.is_equal(lease['address'], fqdn):
                    logger.info(f"Updating Unbound for {address} {lease['hostname']}.{fqdn}")
                    remove_rr.append(f"{address.reverse_pointer}")
                    remove_rr.append(f"{fqdn}")
                    unbound_local_data.cleanup(lease['address'], fqdn)
                    add_rr.append(f"{address.reverse_pointer} PTR {fqdn}")
                    add_rr.append(f"{fqdn} IN A {lease['address']}")
                    unbound_local_data.add_address(lease['address'], fqdn)
    
        # Check for leases that no longer exist
        for address in list(cached_leases):
            if address not in active_addresses:
                logger.info(f"Lease no longer exists: {address}")
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
    parser.add_argument('--pid', help='pid file location', default='/var/run/unbound_systemd_networkd_watcher.pid')
    parser.add_argument('--source', help='source leases directory', default='/run/systemd/netif/leases/')
    parser.add_argument('--target', help='target config file, used when unbound restarts', default='/var/unbound/dhcpleases.conf')
    parser.add_argument('--domain', help='default domain to use', default=DEFAULT_DOMAIN)
    parser.add_argument('--foreground', help='run in foreground', default=False, action='store_true')
    parser.add_argument('--log-level', help='set the logging level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    inputargs = parser.parse_args()

    # Set the logging level based on the argument
    logging.basicConfig(level=getattr(logging, inputargs.log_level), format='%(asctime)s - %(levelname)s - %(message)s')
    syslog.openlog('unbound_systemd_networkd_watcher', facility=syslog.LOG_LOCAL4)

    logger.info(f"Starting unbound_systemd_networkd_watcher with arguments: {vars(inputargs)}")
    if inputargs.foreground:
        logger.info("Running in foreground mode")
        run_watcher(target_filename=inputargs.target, default_domain=inputargs.domain, watch_dir_or_file=inputargs.source)
    else:
        logger.info("Running in daemon mode")
        syslog.syslog(syslog.LOG_NOTICE, 'daemonize unbound systemd-networkd watcher.')
        cmd = lambda: run_watcher(target_filename=inputargs.target, default_domain=inputargs.domain, watch_dir_or_file=inputargs.source)
        daemon = Daemonize(app="unbound_systemd_networkd_watcher", pid=inputargs.pid, action=cmd)
        daemon.start()