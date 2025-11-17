import os
import logging
import json
import time
import sys
import subprocess
import shutil
from argparse import ArgumentParser
import ipaddress
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DEFAULT_DOMAIN = 'lan'
UNBOUND_CONTROL_PATH = None
active_leases = {}

class DirChangeHandler(FileSystemEventHandler):
    def __init__(self, source_dir):
        self.source_dir = source_dir
        logging.debug(f"DirChangeHandler initialized with source: {source_dir}")

    def on_any_event(self, event):
        global active_leases, default_domain
        """Handle any file system event."""
        logging.debug(f"Event detected: {event.event_type} on {event.src_path}")
        if event.event_type  in ("created", "modified") and not event.is_directory:
            try:
                logging.debug(f"Process leases from file: {event.src_path}")
                process_lease_file(event.src_path)
            except Exception as e:
                logging.error(f"Error reading file {event.src_path}: {e}")
        if event.event_type == "deleted":
            try:
                logging.debug(f"Lease file {event.src_path} has been deleted")
                delete_leases_from_file(event.src_path)
            except Exception as e:
                logging.error(f"Error deleting entries from file {event.src_path}")

logger = logging.getLogger(__name__)

def find_unbound_control():
    """Find the unbound-control binary in common locations"""
    global UNBOUND_CONTROL_PATH
    
    if UNBOUND_CONTROL_PATH:
        return UNBOUND_CONTROL_PATH
    
    # Common paths where unbound-control might be located
    common_paths = [
        '/usr/sbin/unbound-control',
        '/sbin/unbound-control', 
        '/usr/local/sbin/unbound-control',
        '/usr/bin/unbound-control',
        '/bin/unbound-control'
    ]
    
    # First try using 'which' command
    try:
        UNBOUND_CONTROL_PATH = shutil.which('unbound-control')
        if UNBOUND_CONTROL_PATH:
            logger.debug(f"Found unbound-control using which: {UNBOUND_CONTROL_PATH}")
            return UNBOUND_CONTROL_PATH
    except Exception as e:
        logger.debug(f"Error using which: {e}")
    
    # Fallback to checking common paths
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            UNBOUND_CONTROL_PATH = path
            logger.debug(f"Found unbound-control at: {UNBOUND_CONTROL_PATH}")
            return UNBOUND_CONTROL_PATH
    
    raise FileNotFoundError("unbound-control binary not found in common locations")

def unbound_control(commands, input=None, server=None, config_file=None):
    """Execute unbound-control command"""
    try:
        unbound_control_path = find_unbound_control()
    except FileNotFoundError as e:
        logger.error(f"Cannot find unbound-control: {e}")
        return
    
    # Build command with optional server specification and config file
    cmd = [unbound_control_path]
    
    # Add config file if provided
    if config_file and os.path.exists(config_file):
        cmd.extend(['-c', config_file])
    
    # Add server specification (IP:port)
    if server:
        cmd.extend(['-s', server])
    
    cmd.extend(commands)

    input_string = None
    if input:
        input_string = '\n'.join(input) + '\n'
    logger.debug(f"Executing unbound-control command: {' '.join(cmd)}")
    result = subprocess.run(cmd, input=input_string, text=True, capture_output=True)
    logger.debug(f"unbound-control output: {result.stdout}")
    if result.stderr:
        logger.error(f"unbound-control error: {result.stderr}")
    
    return result

def apply_unbound_changes(dhcpd_changed, remove_rr, add_rr, server=None, config_file=None):
    """Apply changes to Unbound DNS."""
    if dhcpd_changed:
        if remove_rr:
            logger.info(f"Removing {len(remove_rr)} resource records")
            unbound_control(['local_datas_remove'], input=remove_rr, server=server, config_file=config_file)
        if add_rr:
            logger.info(f"Adding {len(add_rr)} resource records")
            unbound_control(['local_datas'], input=add_rr, server=server, config_file=config_file)

def add_to_unbound(hostname, address) -> list:
    global default_domain
    fqdn = f"{hostname}.{default_domain}"
    add_rr = [
        f"{address.reverse_pointer} PTR {fqdn}",
        f"{fqdn} IN AAAA {address}"
    ]
    return add_rr

def remove_from_unbound(hostname, address) -> list:
    global default_domain
    fqdn = f"{hostname}.{default_domain}"
    remove_rr = [ 
        f"{address.reverse_pointer} PTR {fqdn}",
        f"{fqdn} IN AAAA {address}"
    ]
    return remove_rr

def modify_on_unbound(hostname, address, prev_address) -> tuple:
    remove_rr = remove_from_unbound(hostname,prev_address)
    add_rr = add_to_unbound(hostname,address)
    return add_rr, remove_rr

def extract_leases(data) -> list:
    """Extract leases from json data."""
    leases = []
    for item in data:
        try:
            address = ':'.join(map(str, item['Address']))
            leases.append({
                "address" : ipaddress.ip_address(address),
                "hostname": item.get('Hostname', ''),
                "expire"  : item.get('Expire', ''),
            })
        except KeyError as e:
            logging.error(f"Missing expected key in lease data: {e}")
    return leases

def filter_leases_by_expiration(leases) -> list:
    filtered_leases = {}
    for lease in leases:
        if filtered_leases.get(lease['hostname']) is None:
            filtered_leases[lease['hostname']] = lease
        else:
            if filtered_leases[lease['hostname']]['expire'] < lease['expire']:
                filtered_leases[lease['hostname']] = lease
    return list(filtered_leases.values())

def read_file(file_path) -> list:
    """Read the leases from JSON file."""
    leases = []
    try:
        logging.debug(f"Reading file: {file_path}")
        with open(file_path, 'r') as file:
            data = json.load(file)
            leases.extend(extract_leases(data))
        logging.debug(f"File read successfully: {file_path}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error reading file {file_path}: {e}")
    filtered_leases = filter_leases_by_expiration(leases)
    return filtered_leases

def delete_leases_from_file(file_path, server=None, config_file=None):
    global active_leases
    remove_rr = []
    filename = os.path.basename(file_path)
    logging.debug(f"Removing inactive lease file: {filename}")
    leases_to_remove = list(active_leases[filename].keys())
    for hostname in leases_to_remove:
        logging.info(f"Removing lease of hostname: {hostname} from deleted file: {filename}")
        remove_rr.extend(remove_from_unbound(hostname,active_leases[filename][hostname]))
    dhcp_changed = len(remove_rr) > 0
    apply_unbound_changes(dhcp_changed, remove_rr, [], server=server, config_file=config_file)
    del active_leases[filename]

def _remove_inactive_leases(leases,filename):
    """Remove leases that are no longer present in the source directory."""
    global active_leases
    remove_rr = []
    active_lease_entries = list(active_leases[filename].keys())
    for hostname in active_lease_entries:
        if hostname not in [lease['hostname'] for lease in leases]:
            logging.info(f"Removing inactive lease for hostname: {hostname} from file: {filename}")
            remove_rr.extend(remove_from_unbound(hostname,active_leases[filename][hostname]))
            del active_leases[filename][hostname]
    return remove_rr

def _process_lease_entries(lease_list, filename) -> tuple:
    """Process lease entries and update active leases."""
    global active_leases
    add_rr = []
    remove_rr = []
    for lease in lease_list:
        hostname = lease['hostname']
        address = lease['address']
        prev_address = active_leases[filename].get(hostname)
        if prev_address is None:
            active_leases[filename][hostname] = address
            add_rr.extend(add_to_unbound(hostname,address))
            logging.info(f"New lease added: {hostname} with address {address}")
        elif prev_address != address:
            logging.info(f"Lease for hostname {hostname} has changed from {prev_address} to {address}")
            active_leases[filename][hostname] = address
            add, rem = modify_on_unbound(hostname,address,prev_address)
            add_rr.extend(add)
            remove_rr.extend(rem)
        else:
            logging.debug(f"No change in lease for hostname {hostname} on file {filename}")
    remove_rr.extend(_remove_inactive_leases(lease_list,filename))
    logging.debug(f"Finished processing file: {filename}")
    return add_rr, remove_rr

def process_lease_file(file_path, server=None, config_file=None):
    """Process a single lease file."""
    global active_leases
    logging.info(f"Processing lease file: {file_path}")
    leases = read_file(file_path)
    if leases:
        filename = os.path.basename(file_path)
        active_leases.setdefault(filename, {})
        if not active_leases[filename]:
            logging.info(f"New lease file detected: {filename}")
        add_rr, remove_rr = _process_lease_entries(leases, filename)
        dhcp_changed = len(add_rr) > 0 or len(remove_rr) > 0
        apply_unbound_changes(dhcp_changed, remove_rr, add_rr, server=server, config_file=config_file)
    else:
        logging.warning(f"No valid leases found in file: {file_path}")
    return active_leases

def initial_run(source, server=None, config_file=None):
    """Initial run to process all lease files in the source directory."""
    global active_leases
    logging.info(f"Initial run on source file or directory: {source}")
    if not os.path.exists(source):
        logging.error(f"Source file or directory does not exist: {source}")
        sys.exit(1)
    if os.path.isfile(source):
        logging.info(f"Processing single file: {source}")
        process_lease_file(source, server=server, config_file=config_file)
        return
    if os.path.isdir(source):
        for filename in os.listdir(source):
            process_lease_file(os.path.join(source,filename), server=server, config_file=config_file)
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--log-level', help='set the logging level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    parser.add_argument('--source', help='source leases directory', default='/run/slaac-resolver/')
    parser.add_argument('--domain', help='default domain to use', default=DEFAULT_DOMAIN)
    parser.add_argument('--unbound-server', help='unbound server to connect to (IP:port)', default=None)
    parser.add_argument('--config-file', help='unbound config file path', default=None)

    inputargs = parser.parse_args()

    level = getattr(logging, inputargs.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logging.info(f"Starting SLAAC Resolver Watcher with source: {inputargs.source}")
    logging.info(f"Configuration: server={inputargs.unbound_server}, config_file={inputargs.config_file}")

    default_domain = inputargs.domain

    initial_run(inputargs.source, server=inputargs.unbound_server, config_file=inputargs.config_file)

    event_handler = DirChangeHandler(inputargs.source)
    observer = Observer()
    observer.schedule(event_handler, path=inputargs.source, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()