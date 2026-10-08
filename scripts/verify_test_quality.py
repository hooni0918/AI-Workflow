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

    def test_non_ascii_and_space_paths_are_targets(self):
        # git 은 한글 경로를 8진수로 인용하고 공백 경로 머리줄 끝에 탭을 붙인다 — 그래도 범위에 들어가야 한다
        self.repo.write("Packages/Wallet/Sources/Wallet/잔액.swift", "let a = 1\n")
        self.repo.write("Packages/Wallet/Sources/Wallet/Pay Helper.swift", "let b = 1\n")
        self.repo.commit("add")
        self.repo.write("Packages/Wallet/Sources/Wallet/잔액.swift", "let a = 1 > 0\n")
        self.repo.write("Packages/Wallet/Sources/Wallet/Pay Helper.swift", "let b = 1 > 0\n")
        self.repo.write("Packages/Wallet/Sources/Wallet/새파일.swift", "let c = 2\n")
        targets = self.plan()["modules"]["Wallet"]["targets"]
        self.assertEqual(targets["Packages/Wallet/Sources/Wallet/잔액.swift"], [1])
        self.assertEqual(targets["Packages/Wallet/Sources/Wallet/Pay Helper.swift"], [1])
        self.assertEqual(targets["Packages/Wallet/Sources/Wallet/새파일.swift"], "all")

    def test_diff_attributes_do_not_hide_changed_lines(self):
        self.repo.write(".gitattributes", "*.swift -diff\n")
        self.repo.write(WALLET_PATH, WALLET.replace("balance >= amount", "balance > amount"))
        self.repo.commit("binary attr")
        targets = self.plan()["modules"]["Wallet"]["targets"]
        self.assertEqual(targets, {WALLET_PATH: [5]})

    def test_file_moved_in_from_ignored_location_is_fully_targeted(self):
        self.repo.write("App/Fee.swift", "struct Fee {\n    let ok = 1 >= 0\n}\n")
        self.repo.commit("fee in app")
        self.repo.git("checkout", "-q", "-b", "move")
        self.repo.git("mv", "App/Fee.swift", "Packages/Wallet/Sources/Wallet/Fee.swift")
        self.repo.commit("move")
        self.config["ignore"] = ["App/**"]
        targets = gate.plan_scope(self.repo.path, self.config, base="feature")["modules"]["Wallet"]["targets"]
        self.assertEqual(targets["Packages/Wallet/Sources/Wallet/Fee.swift"], [1, 2, 3])

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


WALLET_PATH = "Packages/Wallet/Sources/Wallet/Wallet.swift"
LABELS_PATH = "Packages/Wallet/Sources/Wallet/Labels.swift"


def mutant(line, status, mutator="RelationalOperatorReplacement", replacement=">", column=9, path=WALLET_PATH):
    return {"file": path, "start_line": line, "start_column": column, "end_line": line,
            "mutator": mutator, "replacement": replacement, "status": status}


def one_module_plan(targets, unmapped=()):
    return {"modules": {"Wallet": {"targets": targets, "widened": False,
                                   "source_changed": list(targets), "test_changed": []}},
            "unmapped": list(unmapped), "ignored": [], "other": []}


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        for rel, content in ((WALLET_PATH, WALLET), (LABELS_PATH, LABELS)):
            os.makedirs(os.path.dirname(os.path.join(self.repo, rel)), exist_ok=True)
            with open(os.path.join(self.repo, rel), "w", encoding="utf-8") as handle:
                handle.write(content)

    def tearDown(self):
        self.tmp.cleanup()

    def judge(self, targets, mutants, decisions=(), counts=None, unmapped=()):
        counts = {"Wallet": len(mutants)} if counts is None else counts
        return gate.judge(self.repo, one_module_plan(targets, unmapped), list(mutants), counts, list(decisions))

    def decision(self, m, kind="equivalent", **extra):
        key, _ = gate.mutant_key(self.repo, m)
        entry = {"key": key, "kind": kind, "reason": "앞 분기가 같은 값을 이미 걸러 동작이 같다",
                 "approved_by": "reviewer"}
        entry.update(extra)
        return entry

    def test_all_killed_passes(self):
        result = self.judge({WALLET_PATH: [5]}, [mutant(5, "Killed")])
        self.assertEqual(result["verdict"], "pass")

    def test_survived_fails_with_hint(self):
        result = self.judge({WALLET_PATH: [5]}, [mutant(5, "Survived")])
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("요구사항", result["unresolved"][0]["hint"])
        self.assertEqual(result["unresolved"][0]["line_text"], "if amount > 0 && balance >= amount {")

    def test_approved_equivalent_decision_resolves(self):
        m = mutant(5, "Survived")
        result = self.judge({WALLET_PATH: [5]}, [m], [self.decision(m)])
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(len(result["resolved"]), 1)

    def test_decision_kind_must_match_status(self):
        m = mutant(5, "Survived")
        result = self.judge({WALLET_PATH: [5]}, [m], [self.decision(m, kind="hang_detected")])
        self.assertEqual(result["verdict"], "fail")

    def test_timeout_needs_hang_decision(self):
        m = mutant(5, "Timeout")
        self.assertEqual(self.judge({WALLET_PATH: [5]}, [m])["verdict"], "fail")
        result = self.judge({WALLET_PATH: [5]}, [m], [self.decision(m, kind="hang_detected")])
        self.assertEqual(result["verdict"], "pass")

    def test_decision_key_survives_line_shift_but_not_line_edit(self):
        m = mutant(5, "Survived")
        key, _ = gate.mutant_key(self.repo, m)
        path = os.path.join(self.repo, WALLET_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("// header\n" + WALLET)
        self.assertEqual(gate.mutant_key(self.repo, mutant(6, "Survived"))[0], key)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("// header\n" + WALLET.replace("amount > 0", "amount > 1"))
        self.assertNotEqual(gate.mutant_key(self.repo, mutant(6, "Survived"))[0], key)

    def test_out_of_scope_mutants_are_not_judged(self):
        result = self.judge({WALLET_PATH: [5]}, [mutant(5, "Killed"), mutant(9, "Survived")])
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["out_of_scope"], 1)

    def test_no_mutants_in_whole_module_is_incomplete(self):
        result = self.judge({WALLET_PATH: [5]}, [], counts={"Wallet": 0})
        self.assertEqual(result["verdict"], "incomplete")

    def test_missing_results_for_line_with_operators_is_incomplete(self):
        # 실측: 도구가 대상 파일을 분석하지 않고 변이 0개·점수 100% 를 낸 경우
        result = self.judge({WALLET_PATH: [5], LABELS_PATH: "all"},
                            [mutant(1, "Killed", path=LABELS_PATH)])
        self.assertEqual(result["verdict"], "incomplete")

    def test_file_without_mutable_operators_is_not_applicable_file(self):
        result = self.judge({WALLET_PATH: [5], LABELS_PATH: [2]}, [mutant(5, "Killed")])
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["no_mutants"], [LABELS_PATH])

    def test_operators_only_in_comments_do_not_block(self):
        path = os.path.join(self.repo, LABELS_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("// balance >= amount\npublic enum Labels {}\n")
        result = self.judge({WALLET_PATH: [5], LABELS_PATH: [1]}, [mutant(5, "Killed")])
        self.assertEqual(result["verdict"], "pass")

    def test_only_compile_errors_is_incomplete(self):
        result = self.judge({WALLET_PATH: [5]}, [mutant(5, "CompileError")])
        self.assertEqual(result["verdict"], "incomplete")

    def test_pending_is_incomplete(self):
        result = self.judge({WALLET_PATH: [5]}, [mutant(5, "Killed"), mutant(5, "Pending", replacement="<")])
        self.assertEqual(result["verdict"], "incomplete")

    def test_unmapped_logic_change_is_incomplete(self):
        result = self.judge({WALLET_PATH: [5]}, [mutant(5, "Killed")], unmapped=["Tools/Gen.swift"])
        self.assertEqual(result["verdict"], "incomplete")

    def test_nothing_in_scope_is_not_applicable(self):
        result = gate.judge(self.repo, one_module_plan({}), [], {}, [])
        self.assertEqual(result["verdict"], "not_applicable")

    def test_suppression_marker_is_unresolved_until_approved(self):
        path = os.path.join(self.repo, WALLET_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("@SwiftMutationTestingDisabled\n" + WALLET)
        plan = one_module_plan({WALLET_PATH: [6]})
        found = gate.suppression_items(self.repo, plan, ["@SwiftMutationTestingDisabled"])
        self.assertEqual([(s["start_line"], s["status"]) for s in found], [(1, "Ignored")])
        result = gate.judge(self.repo, plan, [mutant(6, "Killed")], {"Wallet": 1}, [], suppressions=found)
        self.assertEqual(result["verdict"], "fail")
        approval = self.decision(found[0], kind="ignore_approved")
        result = gate.judge(self.repo, plan, [mutant(6, "Killed")], {"Wallet": 1}, [approval], suppressions=found)
        self.assertEqual(result["verdict"], "pass")

    def test_suppression_marker_in_comment_is_ignored(self):
        path = os.path.join(self.repo, WALLET_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("// @SwiftMutationTestingDisabled 는 쓰지 않는다\n" + WALLET)
        found = gate.suppression_items(self.repo, one_module_plan({WALLET_PATH: [6]}),
                                       ["@SwiftMutationTestingDisabled"])
        self.assertEqual(found, [])

    def test_decision_without_approver_is_rejected(self):
        tmp = os.path.join(self.repo, "decisions.json")
        m = mutant(5, "Survived")
        write_json(tmp, {"decisions": [self.decision(m, approved_by=" ")]})
        valid, invalid = gate.load_decisions(tmp)
        self.assertEqual((len(valid), len(invalid)), (0, 1))


class ResultAndVerifyTests(unittest.TestCase):
    def setUp(self):
        self.repo = GitRepo(BASE_FILES)
        self.outside = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.outside.name, "config.json")
        config = base_config()
        config["modules"][0]["fingerprint"] = ["Packages/Wallet/Package.swift"]
        write_json(self.config_path, config)
        self.config = gate.load_config(self.config_path)
        self.result_path = os.path.join(self.outside.name, "result.json")
        self.report_path = os.path.join(self.outside.name, "report.json")
        self.repo.write(WALLET_PATH, WALLET.replace("amount > 0", "amount >= 1"))
        self.repo.commit("change")

    def tearDown(self):
        self.repo.cleanup()
        self.outside.cleanup()

    def judge_cli(self, status, extra_reports=True):
        write_json(self.report_path, stryker_report("Sources/Wallet/Wallet.swift", [(5, "ROR", ">", status)]))
        args = ["judge", "--config", self.config_path, "--repo", self.repo.path, "--out", self.result_path]
        if extra_reports:
            args += ["--report", f"Wallet={self.report_path}"]
        return gate.main(args)

    def verify_cli(self):
        return gate.main(["verify", "--config", self.config_path, "--repo", self.repo.path,
                          "--result", self.result_path])

    def test_pass_then_verify_passes(self):
        self.assertEqual(self.judge_cli("Killed"), gate.EXIT_PASS)
        self.assertEqual(self.verify_cli(), gate.EXIT_PASS)

    def test_survivor_fails_and_verify_reports_fail(self):
        self.assertEqual(self.judge_cli("Survived"), gate.EXIT_UNRESOLVED)
        self.assertEqual(self.verify_cli(), gate.EXIT_UNRESOLVED)

    def test_test_edit_after_check_makes_result_stale(self):
        self.judge_cli("Killed")
        self.repo.write("Packages/Wallet/Tests/WalletTests/WalletTests.swift", WALLET_TEST + "// weaker\n")
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_decision_edit_after_check_makes_result_stale(self):
        self.judge_cli("Killed")
        write_json(os.path.join(self.repo.path, ".test-quality/decisions.json"), {"decisions": []})
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_commit_rewrite_without_content_change_stays_valid(self):
        self.judge_cli("Killed")
        self.repo.git("commit", "-q", "--amend", "-m", "reworded")
        self.assertEqual(self.verify_cli(), gate.EXIT_PASS)

    def test_missing_result_is_incomplete(self):
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_unresolved_output_shows_original_operator_and_column(self):
        import io
        report = stryker_report("Sources/Wallet/Wallet.swift", [(5, "ROR", ">", "Survived", 34)])
        report["files"]["Sources/Wallet/Wallet.swift"]["mutants"][0]["originalText"] = ">="
        write_json(self.report_path, report)
        result = gate.judge_reports(self.repo.path, self.config_path, self.config,
                                    gate.plan_scope(self.repo.path, self.config),
                                    {"Wallet": self.report_path})
        buffer = io.StringIO()
        gate.print_result(result, out=buffer)
        self.assertIn("Wallet.swift:5:34 ROR >= → >", buffer.getvalue())

    def test_module_in_scope_without_report_is_incomplete(self):
        self.assertEqual(self.judge_cli("Killed", extra_reports=False), gate.EXIT_INCOMPLETE)
        with open(self.result_path, encoding="utf-8") as handle:
            self.assertIn("변이 결과가 없습니다", handle.read())


FAKE_TOOL = r'''
import json, sys, time
report, mode = sys.argv[1], sys.argv[2]
if mode == "sleep":
    time.sleep(5)
if mode == "crash":
    sys.exit(4)
if mode == "silent":
    sys.exit(0)
mutant = {"id": "1", "mutatorName": "RelationalOperatorReplacement", "replacement": "<", "status": mode,
          "location": {"start": {"line": 5, "column": 19}, "end": {"line": 5, "column": 20}}}
with open(report, "w") as handle:
    json.dump({"schemaVersion": "1", "thresholds": {}, "files": {
        "Sources/Wallet/Wallet.swift": {"language": "swift", "source": "", "mutants": [mutant]}}}, handle)
'''


class RunTests(unittest.TestCase):
    def setUp(self):
        self.repo = GitRepo(BASE_FILES)
        self.outside = tempfile.TemporaryDirectory()
        self.fake = os.path.join(self.outside.name, "fake_tool.py")
        with open(self.fake, "w", encoding="utf-8") as handle:
            handle.write(FAKE_TOOL)
        self.repo.write(WALLET_PATH, WALLET.replace("amount > 0", "amount >= 1"))
        self.repo.commit("change")
        self.result_path = os.path.join(self.outside.name, "result.json")
        self.work_dir = os.path.join(self.outside.name, "work")

    def tearDown(self):
        self.repo.cleanup()
        self.outside.cleanup()

    def run_gate(self, mode, baseline=("true",), timeout=60):
        config = base_config()
        config["tool"]["command"] = [sys.executable, self.fake, "{report}", mode]
        config["tool"]["timeout_seconds"] = timeout
        config["modules"][0]["baseline"] = list(baseline)
        config_path = os.path.join(self.outside.name, "config.json")
        write_json(config_path, config)
        code = gate.main(["run", "--config", config_path, "--repo", self.repo.path,
                          "--out", self.result_path, "--work-dir", self.work_dir])
        with open(self.result_path, encoding="utf-8") as handle:
            return code, json.load(handle)

    def test_killed_passes(self):
        code, result = self.run_gate("Killed")
        self.assertEqual((code, result["verdict"]), (gate.EXIT_PASS, "pass"))

    def test_survived_fails(self):
        code, result = self.run_gate("Survived")
        self.assertEqual((code, result["verdict"]), (gate.EXIT_UNRESOLVED, "fail"))

    def test_failing_baseline_is_incomplete(self):
        code, result = self.run_gate("Killed", baseline=("false",))
        self.assertEqual(code, gate.EXIT_INCOMPLETE)
        self.assertIn("기준 테스트", result["incomplete_reasons"][0])

    def test_missing_tool_is_incomplete(self):
        code, result = self.run_gate("Killed", baseline=("no-such-command-xyz",))
        self.assertEqual(code, gate.EXIT_INCOMPLETE)

    def test_tool_crash_is_incomplete(self):
        code, result = self.run_gate("crash")
        self.assertEqual(code, gate.EXIT_INCOMPLETE)
        self.assertEqual(len(result["incomplete_reasons"]), 1)  # 같은 실패를 두 번 적지 않는다

    def test_malformed_report_still_writes_result(self):
        config = base_config()
        broken = os.path.join(self.outside.name, "broken.json")
        with open(broken, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        config_path = os.path.join(self.outside.name, "config.json")
        write_json(config_path, config)
        code = gate.main(["judge", "--config", config_path, "--repo", self.repo.path,
                          "--report", f"Wallet={broken}", "--out", self.result_path])
        self.assertEqual(code, gate.EXIT_INCOMPLETE)
        with open(self.result_path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["verdict"], "incomplete")

    def test_tool_without_report_is_incomplete_even_with_old_report(self):
        self.run_gate("Killed")  # 이전 실행이 결과를 남긴다
        code, result = self.run_gate("silent")
        self.assertEqual(code, gate.EXIT_INCOMPLETE)
        self.assertIn("결과 파일을 만들지 않았습니다", result["incomplete_reasons"][0])

    def test_module_command_overrides_tool_command(self):
        config = base_config()
        config["tool"]["command"] = [sys.executable, self.fake, "{report}", "crash"]
        config["modules"][0]["command"] = [sys.executable, self.fake, "{report}", "Killed"]
        config_path = os.path.join(self.outside.name, "config.json")
        write_json(config_path, config)
        code = gate.main(["run", "--config", config_path, "--repo", self.repo.path,
                          "--out", self.result_path, "--work-dir", self.work_dir])
        self.assertEqual(code, gate.EXIT_PASS)

    def run_with_version(self, printed, expected="1.5.1"):
        config = base_config()
        config["tool"]["version"] = expected
        config["tool"]["command"] = [sys.executable, self.fake, "{report}", "Killed"]
        config["tool"]["version_command"] = [sys.executable, "-c", f"print('tool {printed} [arm64]')"]
        config_path = os.path.join(self.outside.name, "config.json")
        write_json(config_path, config)
        return gate.main(["run", "--config", config_path, "--repo", self.repo.path,
                          "--out", self.result_path, "--work-dir", self.work_dir])

    def test_matching_tool_version_passes(self):
        self.assertEqual(self.run_with_version("1.5.1"), gate.EXIT_PASS)

    def test_other_tool_version_is_incomplete(self):
        # 소스 빌드는 0.0.0-dev 를, 상위 버전은 1.5.10 을 찍는다 — 둘 다 1.5.1 이 아니다
        self.assertEqual(self.run_with_version("0.0.0-dev"), gate.EXIT_INCOMPLETE)
        self.assertEqual(self.run_with_version("1.5.10"), gate.EXIT_INCOMPLETE)

    def test_tool_timeout_is_incomplete(self):
        code, _ = self.run_gate("sleep", timeout=1)
        self.assertEqual(code, gate.EXIT_INCOMPLETE)


if __name__ == "__main__":
    unittest.main(verbosity=1)
