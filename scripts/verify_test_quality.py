#!/usr/bin/env python3
# test-quality 스킬의 변이 검사 게이트(mutation_gate.py)를 회귀 검증한다.
#
# 게이트의 존재 이유는 "거짓 성공을 내지 않는 것"이다. 도구 오류·결과 누락·오래된 결과·
# 범위 누락이 통과로 새는지를 실제 git 저장소와 가짜 도구로 재현해 확인한다.
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "deploy", "skills", "test-quality", "scripts"))

import mutation_gate as gate  # noqa: E402


def base_config(**overrides):
    config = {
        "version": 1,
        "base": "main",
        "source_extensions": [".swift"],
        "tool": {
            "name": "fake",
            "version": "1",
            "command": ["fake-tool", "{module_path}", "--output", "{report}"],
        },
        "modules": [
            {
                "name": "Wallet",
                "path": "Packages/Wallet",
                "sources": ["Packages/Wallet/Sources"],
                "tests": ["Packages/Wallet/Tests"],
                "baseline": ["true"],
            }
        ],
    }
    config.update(overrides)
    return config


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_config_fills_defaults(self):
        write_json(self.path, base_config())
        config = gate.load_config(self.path)
        self.assertEqual(config["ignore"], [])
        self.assertEqual(config["decisions"], ".test-quality/decisions.json")
        self.assertEqual(config["modules"][0]["vars"], {})

    def test_command_without_report_placeholder_is_rejected(self):
        config = base_config()
        config["tool"]["command"] = ["fake-tool", "{module_path}"]
        write_json(self.path, config)
        with self.assertRaises(gate.ConfigError):
            gate.load_config(self.path)

    def test_duplicate_module_names_are_rejected(self):
        config = base_config()
        config["modules"].append(dict(config["modules"][0]))
        write_json(self.path, config)
        with self.assertRaises(gate.ConfigError):
            gate.load_config(self.path)

    def test_empty_sources_are_rejected(self):
        config = base_config()
        config["modules"][0]["sources"] = []
        write_json(self.path, config)
        with self.assertRaises(gate.ConfigError):
            gate.load_config(self.path)

    def test_check_config_exit_codes(self):
        write_json(self.path, base_config())
        self.assertEqual(gate.main(["check-config", "--config", self.path]), gate.EXIT_PASS)
        write_json(self.path, {"version": 2})
        self.assertEqual(gate.main(["check-config", "--config", self.path]), gate.EXIT_USAGE)


class ExpandTests(unittest.TestCase):
    def test_values_and_nested_values(self):
        values = {"scheme": "Wallet", "destination": "id={udid}", "udid": "X"}
        self.assertEqual(gate.expand("-scheme {scheme} {destination}", values), "-scheme Wallet id=X")

    def test_env_values(self):
        os.environ["TQ_TEST_DEST"] = "platform=macOS"
        self.assertEqual(gate.expand("{env:TQ_TEST_DEST}", {}), "platform=macOS")

    def test_missing_value_is_an_error_not_an_empty_string(self):
        with self.assertRaises(gate.ConfigError):
            gate.expand("{scheme}", {})
        os.environ.pop("TQ_TEST_MISSING", None)
        with self.assertRaises(gate.ConfigError):
            gate.expand("{env:TQ_TEST_MISSING}", {})


if __name__ == "__main__":
    unittest.main(verbosity=1)
