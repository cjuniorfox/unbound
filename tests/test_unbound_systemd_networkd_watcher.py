import unittest, sys, os, json
from unittest.mock import patch, mock_open, MagicMock, call
import time
from unbound_systemd_networkd_watcher import (
    parse_systemd_leases,
    UnboundLocalData,
    process_leases,
    cleanup_expired_leases,
    apply_unbound_changes,
)

class TestUnboundSystemdNetworkdWatcher(unittest.TestCase):

    def setUp(self):
        self.default_domain = "home"

        current_time = int(time.time() * 1_000_000) 

        # Mock leases file with properly escaped JSON
        self.leases_file = {
            "BootID":"a4b95e58b4094fa6a04a666af127a5bc",
            "Address":[192,168,1,1],
            "PrefixLength":24,
            "Leases":[
                {
                    "ClientId":[1,124,99,5,54,93,214],
                    "Address":[192,168,1,100],
                    "Hostname":"device1",
                    "ExpirationUSec":72338380895,
                    "ExpirationRealtimeUSec":current_time + 3600 * 1_000_000
                 },{
                     "ClientId":[1,40,175,66,153,139,176],
                     "Address":[192,168,1,101],
                     "Hostname":"device2",
                     "ExpirationUSec":71617267423,
                     "ExpirationRealtimeUSec":current_time + 3600 * 1_000_000
                }
            ]
        }
        self.expired_leases_file = { "BootID":"a4b95e58b4094fa6a04a666af127a5bc",
            "Address":[192,168,1,1],
            "PrefixLength":24,
            "Leases":[
                {
                    "ClientId":[1,124,99,5,54,93,214],
                    "Address":[192,168,1,102],
                    "ExpirationUSec":72338380895,
                    "ExpirationRealtimeUSec":current_time - 3600 * 1_000_000
                 }
            ]
        }

        self.mock_leases_file = json.dumps(self.leases_file)
        self.mock_expired_leases_file = json.dumps(self.expired_leases_file)

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("os.path.isfile", return_value=True)
    def test_parse_systemd_leases_file(self, mock_isfile, mock_open_file):
        # Test parsing leases from a single file
        mock_open_file.return_value.read.return_value = self.mock_leases_file
        leases = parse_systemd_leases("/mock/path/to/leases")
        self.assertEqual(len(leases), 2)
        self.assertEqual(leases[0]["address"], "192.168.1.100")
        self.assertEqual(leases[0]["hostname"], "device1")
        self.assertGreater(leases[0]["expire"], time.time())

    @patch("os.listdir", return_value=["leases1", "leases2"])
    @patch("os.path.isdir", return_value=True)
    @patch("os.path.isfile")
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_systemd_leases_directory(self, mock_open_file, mock_isfile, mock_isdir, mock_listdir):
        # Define behavior for os.path.isfile
        def isfile_side_effect(path):
            return path in ["/mock/path/to/leases_dir/leases1", "/mock/path/to/leases_dir/leases2"]

        mock_isfile.side_effect = isfile_side_effect

        # Define behavior for builtins.open
        def open_side_effect(path, *args, **kwargs):
            if path == "/mock/path/to/leases_dir/leases1":
                return mock_open(read_data=self.mock_leases_file).return_value
            elif path == "/mock/path/to/leases_dir/leases2":
                return mock_open(read_data=self.mock_expired_leases_file).return_value
            raise FileNotFoundError(f"File not found: {path}")

        mock_open_file.side_effect = open_side_effect

        # Test parsing leases from a directory
        leases = parse_systemd_leases("/mock/path/to/leases_dir")
        self.assertEqual(len(leases), 3)
        self.assertIn("192.168.1.100", [lease["address"] for lease in leases])
        self.assertIn("192.168.1.101", [lease["address"] for lease in leases])

    def test_process_leases(self):
        cached_leases = {}
        mock_leases = [
            {
                "address" : ".".join(map(str,self.leases_file['Leases'][0]['Address'])),
                "hostname" : self.leases_file['Leases'][0]['Hostname'],
                "expire" : self.leases_file['Leases'][0]['ExpirationRealtimeUSec'] // 1_000_000,
            },
            {
                "address" : '.'.join(map(str,self.leases_file['Leases'][1]['Address'])),
                "hostname" : self.leases_file['Leases'][1]['Hostname'],
                "expire" : self.leases_file['Leases'][1]['ExpirationRealtimeUSec'] // 1_000_000,
            }
        ]
        unbound_data = UnboundLocalData()
        dhcpd_changed, remove_rr, add_rr = process_leases(
            mock_leases, cached_leases, unbound_data, self.default_domain
        )

        # Assertions
        self.assertTrue(dhcpd_changed)
        self.assertEqual(len(cached_leases), 2)
        self.assertEqual(len(add_rr), 4)  # 2 PTR + 2 A records

    def test_cleanup_expired_leases(self):
        cached_leases = {
            "192.168.1.100": {"address": "192.168.1.100", "hostname": "device1", "expire": time.time() - 3600},
            "192.168.1.101": {"address": "192.168.1.101", "hostname": "device2", "expire": time.time() + 7200},
        }
        active_addresses = {"192.168.1.101"}
        unbound_data = MagicMock()
        remove_rr = []

        dhcpd_changed = cleanup_expired_leases(
            cached_leases, active_addresses, unbound_data, remove_rr, self.default_domain
        )

        # Assertions
        self.assertTrue(dhcpd_changed)
        self.assertEqual(len(cached_leases), 1)
        self.assertEqual(len(remove_rr), 2)  # 1 PTR + 1 A record
        unbound_data.cleanup.assert_called_with("192.168.1.100", "device1.home")

    @patch("unbound_systemd_networkd_watcher.unbound_control")
    def test_apply_unbound_changes(self, mock_unbound_control):
        remove_rr = ["100.168.192.in-addr.arpa", "device1.local"]
        add_rr = ["100.168.192.in-addr.arpa PTR device1.local", "device1.home IN A 192.168.1.100"]

        apply_unbound_changes(True, remove_rr, add_rr)

        # Assertions
        mock_unbound_control.assert_has_calls([
            call(['local_datas_remove'], input=remove_rr),
            call(['local_datas'], input=add_rr),
        ])

    def test_unbound_local_data(self):
        # Test UnboundLocalData functionality
        unbound_data = UnboundLocalData()
        unbound_data.add_address("192.168.1.100", "device1.home")
        self.assertTrue(unbound_data.is_equal("192.168.1.100", "device1.home"))
        unbound_data.cleanup("192.168.1.100", "device1.home")
        self.assertFalse(unbound_data.is_equal("192.168.1.100", "device1.home"))


if __name__ == "__main__":
    unittest.main()