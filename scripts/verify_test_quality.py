#!/usr/bin/env python3
# test-quality 스킬의 변이 검사 게이트(mutation_gate.py)를 회귀 검증한다.
#
# 게이트의 존재 이유는 "거짓 성공을 내지 않는 것"이다. 도구 오류·결과 누락·오래된 결과·
# 범위 누락이 통과로 새는지를 실제 git 저장소와 가짜 도구로 재현해 확인한다.
import json
import os
import subprocess
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


WALLET = """public struct Wallet {
    public private(set) var balance: Int

    public mutating func pay(_ amount: Int) -> Bool {
        if amount > 0 && balance >= amount {
            balance -= amount
            return true
        }
        return false
    }
}
"""

LABELS = 'public enum Labels {\n    public static let title = "wallet"\n}\n'

WALLET_TEST = "import Testing\n@testable import Wallet\n\n@Test func pays() {}\n"


class GitRepo:
    # 임시 git 저장소. main 에 기준 커밋을 만들고 feature 브랜치로 옮겨 변경을 쌓는다.
    def __init__(self, files):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name
        self.git("init", "-q", "-b", "main")
        for rel, content in files.items():
            self.write(rel, content)
        self.commit("base")
        self.git("checkout", "-q", "-b", "feature")

    def git(self, *args):
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.email=t@t", "-c", "user.name=t",
             "-C", self.path, *args],
            check=True, capture_output=True, text=True,
        ).stdout

    def write(self, rel, content):
        full = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(content)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def cleanup(self):
        self.tmp.cleanup()


BASE_FILES = {
    "Packages/Wallet/Sources/Wallet/Wallet.swift": WALLET,
    "Packages/Wallet/Sources/Wallet/Labels.swift": LABELS,
    "Packages/Wallet/Tests/WalletTests/WalletTests.swift": WALLET_TEST,
    "Packages/Wallet/Package.swift": "// manifest\n",
    "App/Screen.swift": "struct Screen {}\n",
    "README.md": "readme\n",
}


def loaded_config(**overrides):
    config = base_config(**overrides)
    config["modules"][0]["fingerprint"] = ["Packages/Wallet/Package.swift"]
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(config, tmp)
    tmp.close()
    try:
        return gate.load_config(tmp.name)
    finally:
        os.unlink(tmp.name)


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


class PlanScopeTests(unittest.TestCase):
    def setUp(self):
        self.repo = GitRepo(BASE_FILES)
        self.config = loaded_config()

    def tearDown(self):
        self.repo.cleanup()

    def plan(self, **kwargs):
        return gate.plan_scope(self.repo.path, self.config, **kwargs)

    def test_source_change_targets_only_changed_lines(self):
        self.repo.write("Packages/Wallet/Sources/Wallet/Wallet.swift",
                        WALLET.replace("balance >= amount", "balance > amount"))
        self.repo.commit("boundary")
        module = self.plan()["modules"]["Wallet"]
        self.assertEqual(module["targets"], {"Packages/Wallet/Sources/Wallet/Wallet.swift": [5]})
        self.assertFalse(module["widened"])

    def test_test_only_change_widens_to_whole_module(self):
        self.repo.write("Packages/Wallet/Tests/WalletTests/WalletTests.swift", WALLET_TEST + "// more\n")
        self.repo.commit("tests")
        module = self.plan()["modules"]["Wallet"]
        self.assertTrue(module["widened"])
        self.assertEqual(module["targets"], {
            "Packages/Wallet/Sources/Wallet/Labels.swift": "all",
            "Packages/Wallet/Sources/Wallet/Wallet.swift": "all",
        })

    def test_source_and_test_change_does_not_widen(self):
        self.repo.write("Packages/Wallet/Sources/Wallet/Wallet.swift", WALLET.replace("return true", "return  true"))
        self.repo.write("Packages/Wallet/Tests/WalletTests/WalletTests.swift", WALLET_TEST + "// more\n")
        self.repo.commit("both")
        module = self.plan()["modules"]["Wallet"]
        self.assertFalse(module["widened"])
        self.assertEqual(list(module["targets"]), ["Packages/Wallet/Sources/Wallet/Wallet.swift"])

    def test_uncommitted_and_untracked_changes_are_included(self):
        self.repo.write("Packages/Wallet/Sources/Wallet/New.swift", "let x = 1 > 0\n")
        self.repo.write("Packages/Wallet/Sources/Wallet/Wallet.swift", WALLET.replace("amount > 0", "amount >= 0"))
        targets = self.plan()["modules"]["Wallet"]["targets"]
        self.assertEqual(targets["Packages/Wallet/Sources/Wallet/New.swift"], "all")
        self.assertEqual(targets["Packages/Wallet/Sources/Wallet/Wallet.swift"], [5])

    def test_unmapped_ignored_and_other_are_separated(self):
        self.repo.write("App/Screen.swift", "struct Screen { let a = 1 }\n")
        self.repo.write("Tools/Gen.swift", "let gen = 1\n")
        self.repo.write("README.md", "changed\n")
        self.repo.write("Packages/Wallet/Package.swift", "// manifest 2\n")
        self.repo.commit("misc")
        self.config["ignore"] = ["App/**"]
        plan = self.plan()
        self.assertEqual(plan["unmapped"], ["Tools/Gen.swift"])
        self.assertEqual(plan["ignored"], ["App/Screen.swift"])
        self.assertEqual(plan["other"], ["README.md"])
        self.assertEqual(plan["modules"]["Wallet"]["targets"], {})

    def test_deletion_only_hunk_targets_neighbor_lines(self):
        self.repo.write("Packages/Wallet/Sources/Wallet/Wallet.swift",
                        WALLET.replace("            balance -= amount\n", ""))
        self.repo.commit("drop line")
        targets = self.plan()["modules"]["Wallet"]["targets"]
        self.assertEqual(targets["Packages/Wallet/Sources/Wallet/Wallet.swift"], [5, 6])

    def test_deleted_source_counts_as_source_change_without_targets(self):
        self.repo.git("rm", "-q", "Packages/Wallet/Sources/Wallet/Labels.swift")
        self.repo.commit("delete")
        module = self.plan()["modules"]["Wallet"]
        self.assertEqual(module["source_changed"], ["Packages/Wallet/Sources/Wallet/Labels.swift"])
        self.assertEqual(module["targets"], {})
        self.assertFalse(module["widened"])

    def test_unknown_base_is_incomplete_not_empty(self):
        with self.assertRaises(gate.IncompleteError):
            self.plan(base="no-such-branch")


def stryker_report(file_key, mutants, project_root=None):
    report = {"schemaVersion": "1", "thresholds": {"high": 80, "low": 60}, "files": {
        file_key: {"language": "swift", "source": "", "mutants": [
            {"id": str(i), "mutatorName": m[1], "replacement": m[2], "status": m[3],
             "location": {"start": {"line": m[0], "column": m[4] if len(m) > 4 else 5},
                          "end": {"line": m[0], "column": 30}}}
            for i, m in enumerate(mutants)
        ]}}}
    if project_root:
        report["projectRoot"] = project_root
    return report


class ReportTests(unittest.TestCase):
    KNOWN = ["Packages/Wallet/Sources/Wallet/Wallet.swift", "Packages/Wallet/Sources/Wallet/Labels.swift"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        for rel in self.KNOWN:
            os.makedirs(os.path.dirname(os.path.join(self.repo, rel)), exist_ok=True)
            open(os.path.join(self.repo, rel), "w").close()
        self.module_root = os.path.join(self.repo, "Packages/Wallet")
        self.report = os.path.join(self.repo, "report.json")

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, key, mutants, project_root=None):
        write_json(self.report, stryker_report(key, mutants, project_root))
        return gate.load_report(self.report, self.repo, [self.module_root], self.KNOWN)

    def test_relative_to_module_root(self):
        mutants, unresolved = self.load("Sources/Wallet/Wallet.swift", [(5, "ROR", ">", "Survived")])
        self.assertEqual(mutants[0]["file"], "Packages/Wallet/Sources/Wallet/Wallet.swift")
        self.assertEqual(unresolved, [])

    def test_absolute_key(self):
        key = os.path.join(self.repo, "Packages/Wallet/Sources/Wallet/Labels.swift")
        mutants, _ = self.load(key, [(1, "ROR", ">", "Killed")])
        self.assertEqual(mutants[0]["file"], "Packages/Wallet/Sources/Wallet/Labels.swift")

    def test_truncated_key_from_symlinked_root_is_matched_by_suffix(self):
        # 실측: projectRoot 가 /tmp/..., 실제 경로가 /private/tmp/... 이면 키 앞부분이 잘린다
        mutants, _ = self.load("et/Sources/Wallet/Wallet.swift", [(5, "ROR", ">", "Killed")])
        self.assertEqual(mutants[0]["file"], "Packages/Wallet/Sources/Wallet/Wallet.swift")

    def test_unknown_key_is_reported_not_guessed(self):
        mutants, unresolved = self.load("Elsewhere/Other.swift", [(1, "ROR", ">", "Killed")])
        self.assertEqual(mutants, [])
        self.assertEqual(unresolved, ["Elsewhere/Other.swift"])

    def test_unknown_status_is_incomplete(self):
        with self.assertRaises(gate.IncompleteError):
            self.load("Sources/Wallet/Wallet.swift", [(5, "ROR", ">", "Maybe")])

    def test_missing_or_malformed_report_is_incomplete(self):
        with self.assertRaises(gate.IncompleteError):
            gate.load_report(os.path.join(self.repo, "none.json"), self.repo, [], self.KNOWN)
        write_json(self.report, {"schemaVersion": "1"})
        with self.assertRaises(gate.IncompleteError):
            gate.load_report(self.report, self.repo, [], self.KNOWN)


if __name__ == "__main__":
    unittest.main(verbosity=1)
