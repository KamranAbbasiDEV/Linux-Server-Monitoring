import unittest
from unittest.mock import patch

from linuxops.collect import (MonitorError, cpu_counters, cpu_usage,
                               memory_usage, network_totals, service_status)


class ProcfsParsingTests(unittest.TestCase):
    def test_cpu_counters(self):
        self.assertEqual(cpu_counters("cpu  10 20 30 40 5 6 7 8\ncpu0 1 2 3 4"), (126, 45))

    def test_cpu_usage(self):
        self.assertEqual(cpu_usage((100, 20), (200, 45)), 75)

    def test_cpu_invalid_delta(self):
        with self.assertRaises(MonitorError):
            cpu_usage((100, 20), (100, 20))

    def test_cpu_bad_values(self):
        with self.assertRaises(MonitorError):
            cpu_counters("cpu a b c d")

    def test_memory_available(self):
        text = "MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 250 kB\n"
        self.assertEqual(memory_usage(text), 75)

    def test_memory_fallback(self):
        text = "MemTotal: 1000 kB\nMemFree: 100 kB\nBuffers: 50 kB\nCached: 200 kB"
        self.assertEqual(memory_usage(text), 65)

    def test_memory_missing(self):
        with self.assertRaises(MonitorError):
            memory_usage("MemFree: 12 kB")

    def test_network_excludes_loopback(self):
        data = "Inter-| Receive | Transmit\n face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed\n  lo: 500 0 0 0 0 0 0 0 900 0 0 0 0 0 0 0\neth0: 1000 0 0 0 0 0 0 0 2000 0 0 0 0 0 0 0\n"
        self.assertEqual(network_totals(data), (1000, 2000))

    def test_network_no_external_interface(self):
        self.assertEqual(network_totals("header\nheader\nlo: 1 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0\n"), (0, 0))

    def test_service_no_shell(self):
        with patch("linuxops.collect.subprocess.run") as run:
            run.return_value.stdout = "active\n"
            self.assertEqual(service_status("nginx"), "active")
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], ["systemctl", "is-active", "--", "nginx"])
            self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_service_name_rejected(self):
        with self.assertRaises(ValueError):
            service_status("nginx;rm -rf /tmp")


if __name__ == "__main__":
    unittest.main()
