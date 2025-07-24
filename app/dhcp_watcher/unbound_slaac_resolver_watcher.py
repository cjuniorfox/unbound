import os
import time
import ipaddress
import subprocess
import syslog
import argparse
import logging
import json
from daemonize import Daemonize

DEFAULT_DOMAIN = 'lan'
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
    logger.debug(f"Executing unbound-control command: {commands} with input: {input_string}")
    result = subprocess.run(['/usr/sbin/unbound-control'] + commands, input=input_string, text=True, capture_output=True)
    logger.debug(f"unbound-control output: {result.stdout}")
    if result.stderr:
        logger.error(f"unbound-control error: {result.stderr}")

def parse_slaac_leases(dir_or_file):
    """Parse leases from a file or directory."""
    leases = []
    if os.path.isfile(dir_or_file):
        leases.extend(parse_leases_from_file(dir_or_file))
    elif os.path.isdir(dir_or_file):
        leases.extend(parse_leases_from_directory(dir_or_file))
    else:
        logger.warning(f"Leases path not found: {dir_or_file}")
    return leases


def parse_leases_from_file(file):
    """Parse leases from a single file."""
    leases = []
    try:
        with open(file, 'r') as f:
            data = json.load(f)
            leases.extend(extract_leases(data,file))
        logger.debug(f"Parsed leases from file: {file}")
    except Exception as e:
        logger.error(f"Failed to parse file {file}: {e}")
    return leases


def parse_leases_from_directory(directory_path):
    """Parse leases from all files in a directory."""
    leases = []
    for filename in os.listdir(directory_path) :
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path) and filename.endswith('.json'):
            leases.extend(parse_leases_from_file(file_path))
    return leases


def extract_leases(data, file):
    """Extract lease information from JSON data."""
    leases = []
    filename = os.path.splitext(os.path.basename(file))[0]
    for lease in data:
        try:
            leases.append({
                'address': ':'.join(map(str, lease['Address'])),
                'hostname': lease.get('Hostname', ''),
                'lease': filename,
            })
        except KeyError as e:
            logger.warning(f"Missing expected key in lease data: {e}")
    return leases

def run_watcher(default_domain, watch_dir_or_file):
    logger.info(f"Starting watcher default_domain={default_domain}, watch_directory={watch_dir_or_file}")
    unbound_local_data = UnboundLocalData()
    cached_leases = {}

    while True:
        logger.debug("Starting new iteration of lease processing")
        leases = parse_slaac_leases(watch_dir_or_file)
        active_addresses = {lease['address'] for lease in leases}

        # Process new or updated leases
        dhcpd_changed, remove_rr, add_rr = process_leases(
            leases, cached_leases, unbound_local_data, default_domain
        )

        # Handle missing leases
        dhcpd_changed |= cleanup_missing_leases(
            cached_leases, active_addresses, unbound_local_data, remove_rr, default_domain
        )

        # Apply changes to Unbound
        apply_unbound_changes(dhcpd_changed, remove_rr, add_rr)

        # Sleep before the next iteration
        time.sleep(5)

def process_leases(leases, cached_leases, unbound_local_data, default_domain):
    dhcpd_changed = False
    remove_rr = []
    add_rr = []

    for lease in leases:
        if lease['hostname'] and lease['address'] and lease.get('lease'):
            key = (lease['hostname'], lease['lease'])
            address = ipaddress.ip_address(lease['address'])
            fqdn = f"{lease['hostname']}.{default_domain}"

            prev_lease = cached_leases.get(key)
            prev_address = prev_lease['address'] if prev_lease else None

            # Only if the address changed for this (hostname, lease) pair
            if prev_address != lease['address']:
                if prev_lease:
                    old_address = ipaddress.ip_address(prev_address)
                    remove_rr.append(f"{old_address.reverse_pointer}")
                    remove_rr.append(f"{fqdn}")
                    unbound_local_data.cleanup(prev_address, fqdn)
                cached_leases[key] = {'address': lease['address'], 'hostname': lease['hostname'], 'lease': lease['lease']}
                dhcpd_changed = True
                logger.debug(f"Lease added/updated: {lease}")

            # Only add if not already present in UnboundLocalData
            if not unbound_local_data.is_equal(lease['address'], fqdn):
                logger.info(f"Updating Unbound for {address} {fqdn}")
                add_rr.append(f"{address.reverse_pointer} PTR {fqdn}")
                add_rr.append(f"{fqdn} IN AAAA {lease['address']}")
                unbound_local_data.add_address(lease['address'], fqdn)

    return dhcpd_changed, remove_rr, add_rr

def cleanup_missing_leases(cached_leases, active_addresses, unbound_local_data, remove_rr, default_domain):
    """Clean up expired or missing leases."""
    dhcpd_changed = False

    # Build set of active (hostname, lease) keys from active_addresses
    active_keys = set()
    for key, lease in cached_leases.items():
        if lease['address'] in active_addresses:
            active_keys.add(key)

    for key in list(cached_leases):
        lease = cached_leases[key]
        if lease['address'] not in active_addresses:
            fqdn = f"{lease['hostname']}.{default_domain}"
            logger.info(f"Lease no longer exists: {lease['address']} ({key})")
            address = ipaddress.ip_address(lease['address'])
            remove_rr.append(f"{address.reverse_pointer}")
            remove_rr.append(f"{fqdn}")
            unbound_local_data.cleanup(lease['address'], fqdn)
            del cached_leases[key]
            dhcpd_changed = True

    return dhcpd_changed


def apply_unbound_changes(dhcpd_changed, remove_rr, add_rr):
    """Apply changes to Unbound DNS."""
    if dhcpd_changed:
        if remove_rr:
            logger.info(f"Removing {len(remove_rr)} resource records")
            unbound_control(['local_datas_remove'], input=remove_rr)
        if add_rr:
            logger.info(f"Adding {len(add_rr)} resource records")
            unbound_control(['local_datas'], input=add_rr)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', help='pid file location', default='/var/run/unbound_slaac_resolver_watcher.pid')
    parser.add_argument('--source', help='source leases directory', default='/run/slaac-resolver/')
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
        run_watcher(default_domain=inputargs.domain, watch_dir_or_file=inputargs.source)
    else:
        logger.info("Running in daemon mode")
        syslog.syslog(syslog.LOG_NOTICE, 'daemonize unbound systemd-networkd watcher.')
        cmd = lambda: run_watcher(default_domain=inputargs.domain, watch_dir_or_file=inputargs.source)
        daemon = Daemonize(app="unbound_systemd_networkd_watcher", pid=inputargs.pid, action=cmd)
        daemon.start()