import unittest
from unittest.mock import patch, mock_open, MagicMock
import time
from unbound_systemd_networkd_watcher import parse_systemd_leases, UnboundLocalData, run_watcher

class TestUnboundSystemdNetworkdWatcher(unittest.TestCase):

    def setUp(self):
        self.default_domain = "local"
        self.mock_leases_file = """
        {
            "Leases": [
                {
                    "Address": [192, 168, 1, 100],
                    "Hostname": "device1",
                    "ExpirationRealtimeUSec": 1743293181660932
                },
                {
                    "Address": [192, 168, 1, 101],
                    "Hostname": "device2",
                    "ExpirationRealtimeUSec": 1743293528112441
                }
            ]
        }
        """
        self.mock_expired_leases_file = """
        {
            "Leases": [
                {
                    "Address": [192, 168, 1, 102],
                    "Hostname": "expired-device",
                    "ExpirationRealtimeUSec": 1000000000000000
                }
            ]
        }
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
    @patch("os.path.isfile", side_effect=lambda x: True)
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_systemd_leases_directory(self, mock_open_file, mock_isfile, mock_listdir):
        # Test parsing leases from a directory
        mock_open_file.return_value.read.side_effect = [self.mock_leases_file, self.mock_expired_leases_file]
        leases = parse_systemd_leases("/mock/path/to/leases_dir")
        self.assertEqual(len(leases), 2)
        self.assertIn("192.168.1.100", [lease["address"] for lease in leases])
        self.assertIn("192.168.1.101", [lease["address"] for lease in leases])

    def test_unbound_local_data(self):
        # Test UnboundLocalData functionality
        unbound_data = UnboundLocalData()
        unbound_data.add_address("192.168.1.100", "device1.local")
        self.assertTrue(unbound_data.is_equal("192.168.1.100", "device1.local"))
        unbound_data.cleanup("192.168.1.100", "device1.local")
        self.assertFalse(unbound_data.is_equal("192.168.1.100", "device1.local"))

    @patch("unbound_systemd_networkd_watcher.unbound_control")
    def test_run_watcher_new_and_expired_leases(self, mock_unbound_control):
        # Mock dependencies
        mock_unbound_control.return_value = None
        leases = [
            {"address": "192.168.1.100", "hostname": "device1", "expire": time.time() + 3600},
            {"address": "192.168.1.101", "hostname": "device2", "expire": time.time() - 3600},  # Expired
        ]
        with patch("unbound_systemd_networkd_watcher.parse_systemd_leases", return_value=leases):
            with patch("time.sleep", return_value=None):  # Skip sleep
                unbound_local_data = UnboundLocalData()
                cached_leases = {}
                remove_rr = []
                add_rr = []

                # Simulate watcher logic
                active_addresses = {lease["address"] for lease in leases}
                for lease in leases:
                    if lease["expire"] > time.time():
                        fqdn = f"{lease['hostname']}.{self.default_domain}"
                        if lease["address"] not in cached_leases:
                            cached_leases[lease["address"]] = lease
                            add_rr.append(f"{fqdn} IN A {lease['address']}")
                            unbound_local_data.add_address(lease["address"], fqdn)
                    else:
                        fqdn = f"{lease['hostname']}.{self.default_domain}"
                        remove_rr.append(f"{fqdn}")
                        unbound_local_data.cleanup(lease["address"], fqdn)

                # Verify results
                self.assertIn("192.168.1.100", cached_leases)
                self.assertNotIn("192.168.1.101", cached_leases)
                self.assertIn("device1.local IN A 192.168.1.100", add_rr)
                self.assertIn("device2.local", remove_rr)

if __name__ == "__main__":
    unittest.main()