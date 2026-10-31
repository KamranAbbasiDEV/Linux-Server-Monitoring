import copy
import unittest

from linuxops.policy import DEFAULT_CONFIG, evaluate, validate_config


METRICS = {"cpu_percent": 20, "memory_percent": 40, "disk_percent": 30,
           "load_1m": 0.2, "load_5m": 0.1, "load_15m": 0.1,
           "uptime_seconds": 100, "network_bytes_received": 10,
           "network_bytes_sent": 20, "services": []}


class PolicyTests(unittest.TestCase):
    def test_no_alerts(self):
        result = evaluate(METRICS, DEFAULT_CONFIG, source="test", host="fixture")
        self.assertEqual(result["overall_status"], "healthy")
        self.assertEqual(result["alerts"], [])

    def test_warning_boundary(self):
        metrics = {**METRICS, "cpu_percent": 80}
        result = evaluate(metrics, DEFAULT_CONFIG, source="test", host="fixture")
        self.assertEqual(result["overall_status"], "warning")
        self.assertEqual(result["alerts"][0]["threshold"], 80)

    def test_critical_boundary(self):
        metrics = {**METRICS, "memory_percent": 92}
        result = evaluate(metrics, DEFAULT_CONFIG, source="test", host="fixture")
        self.assertEqual(result["overall_status"], "critical")

    def test_failed_service_is_critical(self):
        metrics = {**METRICS, "services": [{"name": "nginx", "state": "failed"}]}
        result = evaluate(metrics, DEFAULT_CONFIG, source="test", host="fixture")
        self.assertEqual(result["overall_status"], "critical")
        self.assertEqual(result["alerts"][0]["metric"], "service")

    def test_unavailable_service_is_warning(self):
        metrics = {**METRICS, "services": [{"name": "nginx", "state": "unavailable"}]}
        self.assertEqual(evaluate(metrics, DEFAULT_CONFIG, source="test", host="fixture")["overall_status"], "warning")

    def test_threshold_reversed_rejected(self):
        conf = copy.deepcopy(DEFAULT_CONFIG)
        conf["thresholds"]["cpu_percent"] = {"warning": 97, "critical": 85}
        with self.assertRaises(ValueError):
            validate_config(conf)

    def test_bad_service_name_rejected(self):
        conf = copy.deepcopy(DEFAULT_CONFIG)
        conf["services"] = ["nginx;echo"]
        with self.assertRaises(ValueError):
            validate_config(conf)

    def test_bad_metric_value_rejected(self):
        with self.assertRaises(ValueError):
            evaluate({**METRICS, "cpu_percent": -1}, DEFAULT_CONFIG, source="test", host="fixture")

    def test_bool_is_not_valid_metric(self):
        with self.assertRaises(ValueError):
            evaluate({**METRICS, "memory_percent": True}, DEFAULT_CONFIG, source="test", host="fixture")


if __name__ == "__main__":
    unittest.main()
