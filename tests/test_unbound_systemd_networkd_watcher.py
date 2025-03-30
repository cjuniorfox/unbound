import unittest, sys, os
from unittest.mock import patch, mock_open, MagicMock
import time
from unbound_systemd_networkd_watcher import parse_systemd_leases, UnboundLocalData, run_watcher

class TestUnboundSystemdNetworkdWatcher(unittest.TestCase):

    def setUp(self):
        self.default_domain = "local"
        current_time = int(time.time() * 1_000_000)  # Convert current time to microseconds
    
        # Mock leases file with properly escaped JSON
        # Lease 192.168.1.100 - 1 hour in the future
        # Lease 192.168.1.102 - 2 hours in the future
        self.mock_leases_file = f"""
        {{
            "Leases": [
                {{
                    "Address": [192, 168, 1, 100],
                    "Hostname": "device1",
                    "ExpirationRealtimeUSec": {current_time + 3600 * 1_000_000}
                }},
                {{
                    "Address": [192, 168, 1, 101],
                    "Hostname": "device2",
                    "ExpirationRealtimeUSec": {current_time + 7200 * 1_000_000}
                }}
            ]
        }}
        """
        # 1 hour in the past
        self.mock_expired_leases_file = f"""
        {{
            "Leases": [
                {{
                    "Address": [192, 168, 1, 102],
                    "Hostname": "expired-device",
                    "ExpirationRealtimeUSec": {current_time - 3600 * 1_000_000}
                }}
            ]
        }}
        """
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

    def test_unbound_local_data(self):
        # Test UnboundLocalData functionality
        unbound_data = UnboundLocalData()
        unbound_data.add_address("192.168.1.100", "device1.local")
        self.assertTrue(unbound_data.is_equal("192.168.1.100", "device1.local"))
        unbound_data.cleanup("192.168.1.100", "device1.local")
        self.assertFalse(unbound_data.is_equal("192.168.1.100", "device1.local"))

    

if __name__ == "__main__":
    unittest.main()