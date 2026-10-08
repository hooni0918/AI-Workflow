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
            "version_command": [sys.executable, "-c", "print('fake 1')"],
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

    def test_tool_config_files_must_be_names(self):
        for bad in ("x.yml", [""], [1]):
            write_json(self.path, base_config(tool=dict(base_config()["tool"], config_files=bad)))
            with self.assertRaises(gate.ConfigError):
                gate.load_config(self.path)

    def test_lists_and_vars_must_have_the_right_shape(self):
        # 문자열 하나를 목록 자리에 쓰면 글자 단위로 풀려 범위가 조용히 틀어진다
        bad_configs = [base_config(ignore="App/**")]
        for key, value in (("sources", "Packages/Wallet/Sources"), ("tests", [1]),
                           ("fingerprint", "Package.swift"), ("vars", ["scheme"]), ("vars", {"scheme": 1})):
            config = base_config()
            config["modules"][0][key] = value
            bad_configs.append(config)
        for config in bad_configs:
            write_json(self.path, config)
            with self.assertRaises(gate.ConfigError):
                gate.load_config(self.path)

    def test_version_command_is_required(self):
        config = base_config()
        del config["tool"]["version_command"]
        write_json(self.path, config)
        with self.assertRaises(gate.ConfigError):
            gate.load_config(self.path)

    def test_decisions_path_is_fixed(self):
        # 보호 훅·CODEOWNERS 가 지키는 .test-quality/ 밖으로 옮기지 못하게 한다
        write_json(self.path, base_config(decisions="docs/decisions.json"))
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

    def test_test_change_with_only_resource_delete_or_comment_still_widens(self):
        # 리뷰 재현: 테스트 단언을 지우면서 리소스·삭제·주석만 함께 바꾸면 넓히지 않아 해당 없음이 됐다
        cases = {
            "resource": lambda: self.repo.write("Packages/Wallet/Sources/Wallet/Resources/strings.json", "{}\n"),
            "delete": lambda: os.remove(os.path.join(self.repo.path, LABELS_PATH)),
            "comment": lambda: self.repo.write(LABELS_PATH, "// note\n" + LABELS),
        }
        for name, change in cases.items():
            with self.subTest(name):
                self.repo.git("checkout", "-q", "-B", f"case-{name}", "feature")
                self.repo.write("Packages/Wallet/Tests/WalletTests/WalletTests.swift", WALLET_TEST.replace("pays", "weaker"))
                change()
                self.repo.commit(name)
                module = gate.plan_scope(self.repo.path, self.config, base="feature")["modules"]["Wallet"]
                self.assertTrue(module["widened"])
                self.assertEqual(module["targets"].get(WALLET_PATH), "all")

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

    def test_folder_mismatch_with_same_file_name_is_not_guessed(self):
        # 이름만 같은 다른 위치의 파일 결과가 검사 대상 파일로 섞이면 안 된다
        for key in ("Elsewhere/Wallet.swift", "/somewhere/else/Wallet.swift"):
            mutants, unresolved = self.load(key, [(1, "ROR", ">", "Killed")])
            self.assertEqual((mutants, unresolved), ([], [key]))

    def test_bare_file_name_is_matched_only_when_unique(self):
        mutants, _ = self.load("Labels.swift", [(1, "ROR", ">", "Killed")])
        self.assertEqual(mutants[0]["file"], "Packages/Wallet/Sources/Wallet/Labels.swift")

    def test_malformed_mutant_list_is_incomplete(self):
        write_json(self.report, {"files": {"Sources/Wallet/Wallet.swift": {"mutants": {"0": {}}}}})
        with self.assertRaises(gate.IncompleteError):
            gate.load_report(self.report, self.repo, [self.module_root], self.KNOWN)
        with open(self.report, "wb") as handle:
            handle.write(b'{"files": "\xff"}')
        with self.assertRaises(gate.IncompleteError):
            gate.load_report(self.report, self.repo, [self.module_root], self.KNOWN)

    def test_tool_specific_statuses_are_mapped(self):
        # swift-mutation-testing 1.5.1 소스: unviable → "Unviable", killedByCrash → "Crash"
        write_json(self.report, stryker_report("Sources/Wallet/Wallet.swift",
                                               [(5, "ROR", ">", "Unviable"), (6, "ROR", "<", "Crash")]))
        mutants, _ = gate.load_report(self.report, self.repo, [self.module_root], self.KNOWN,
                                      {"Unviable": "CompileError", "Crash": "RuntimeError"})
        self.assertEqual([m["status"] for m in mutants], ["CompileError", "RuntimeError"])
        with self.assertRaises(gate.IncompleteError):
            gate.load_report(self.report, self.repo, [self.module_root], self.KNOWN)

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
        key, line_text = gate.mutant_key(self.repo, m)
        entry = {"key": key, "file": m["file"], "line_text": line_text, "kind": kind,
                 "reason": "앞 분기가 같은 값을 이미 걸러 동작이 같다", "approved_by": "reviewer"}
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

    def test_changed_line_with_operators_but_no_mutant_is_unresolved(self):
        # 실측: 도구가 대상 파일을 분석하지 않고 변이 0개·점수 100% 를 낸 경우
        result = self.judge({WALLET_PATH: [5], LABELS_PATH: "all"},
                            [mutant(1, "Killed", path=LABELS_PATH)])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual([(m["status"], m["start_line"]) for m in result["unresolved"]], [("NoMutant", 5)])

    def test_skipped_line_is_caught_even_when_file_has_other_mutants(self):
        # 같은 파일 다른 줄에 변이가 있어도, 바뀐 7행(return true)에 변이가 없으면 올린다
        result = self.judge({WALLET_PATH: [5, 7]}, [mutant(5, "Killed")])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual([(m["status"], m["start_line"], m["original"]) for m in result["unresolved"]],
                         [("NoMutant", 7, "true")])

    def test_approved_no_mutant_decision_resolves(self):
        first = self.judge({WALLET_PATH: [5, 7]}, [mutant(5, "Killed")])["unresolved"][0]
        entry = {"key": first["key"], "file": first["file"], "line_text": first["line_text"],
                 "kind": "no_mutant_expected", "reason": "도구가 이 표기를 변이하지 않는다", "approved_by": "reviewer"}
        result = self.judge({WALLET_PATH: [5, 7]}, [mutant(5, "Killed")], [entry])
        self.assertEqual(result["verdict"], "pass")
        wrong_kind = dict(entry, kind="equivalent")
        self.assertEqual(self.judge({WALLET_PATH: [5, 7]}, [mutant(5, "Killed")], [wrong_kind])["verdict"], "fail")

    def test_whole_file_target_is_checked_per_file_not_per_line(self):
        # 넓힘·이동으로 파일 전체가 대상이면 바뀌지 않은 줄까지 줄마다 올리지 않는다
        self.assertEqual(self.judge({WALLET_PATH: "all"}, [mutant(5, "Killed")])["verdict"], "pass")
        result = self.judge({WALLET_PATH: "all"}, [], counts={"Wallet": 1})
        self.assertEqual([(m["status"], m["start_line"]) for m in result["unresolved"]], [("NoMutant", 5)])

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

    def test_mutable_token_ignores_strings_comments_and_operator_names(self):
        found = {line: (gate._mutable_token(line) or (None, None))[1] for line in (
            '    let url = "https://a.b/c == d"',
            "    static func == (lhs: A, rhs: A) -> Bool {",
            '    let name = "a" + suffix',
            "    let x = a ?? b",
            "    if let x = y {",
            "#if DEBUG",
            "    } while running",
            "     * block comment > text",
            "    let total = price * quantity",
            "    let v = cond ? 1 : 2",
            "    guard isValid else { return }",
            "    var isOn = false // toggle",
        )}
        self.assertEqual(list(found.values()),
                         [None, None, None, None, None, None, None, None, "*", "?", "guard", "false"])

    def test_operators_inside_multiline_string_are_not_mutable(self):
        path = os.path.join(self.repo, LABELS_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('public enum Labels {\n    public static let help = """\n    if amount > 0 then pay\n    """\n}\n')
        result = self.judge({WALLET_PATH: [5], LABELS_PATH: [3]}, [mutant(5, "Killed")])
        self.assertEqual((result["verdict"], result["no_mutants"]), ("pass", [LABELS_PATH]))

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

    def test_suppression_marker_after_slashes_in_string_is_found(self):
        # 리뷰 재현: 같은 줄 앞쪽 문자열에 // 가 있으면 뒤의 표식을 놓쳤다. 주석 속 표기도 올리는 쪽이 안전하다
        path = os.path.join(self.repo, WALLET_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('@available(*, deprecated, message: "see https://wiki") @SwiftMutationTestingDisabled\n'
                         + WALLET)
        found = gate.suppression_items(self.repo, one_module_plan({WALLET_PATH: [6]}),
                                       ["@SwiftMutationTestingDisabled"])
        self.assertEqual([s["start_line"] for s in found], [1])

    def test_one_suppression_approval_does_not_cover_a_new_marker(self):
        path = os.path.join(self.repo, WALLET_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("@SwiftMutationTestingDisabled\nfunc legacy() {}\n\n"
                         "@SwiftMutationTestingDisabled\nfunc refund() {}\n")
        plan = one_module_plan({WALLET_PATH: [4, 5]})
        found = gate.suppression_items(self.repo, plan, ["@SwiftMutationTestingDisabled"])
        approval = self.decision(found[0], kind="ignore_approved")
        result = gate.judge(self.repo, plan, [mutant(1, "Killed")], {"Wallet": 1}, [approval], suppressions=found)
        self.assertEqual([i["start_line"] for i in result["resolved"]], [1])
        self.assertEqual([i["start_line"] for i in result["unresolved"]], [4])

    def test_approval_does_not_transfer_to_same_shaped_line_elsewhere(self):
        # 리뷰 재현: guard 줄이 같은 다른 함수를 추가하면 기존 equivalent 승인이 새 변이까지 해소했다
        path = os.path.join(self.repo, WALLET_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("func clampA(_ v: Int) -> Int {\n    guard v >= 0 else { return 0 }\n    return v\n}\n"
                         "func clampB(_ v: Int) -> Int {\n    guard v >= 0 else { return 0 }\n    return v + 1\n}\n")
        old = mutant(2, "Survived", column=13)
        new = mutant(6, "Survived", column=13)
        result = self.judge({WALLET_PATH: [5, 6, 7, 8]}, [new], [self.decision(old)])
        self.assertEqual(result["verdict"], "fail")

    def test_identical_spots_cannot_be_resolved_by_one_decision(self):
        path = os.path.join(self.repo, WALLET_PATH)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("let a = x >= 0\n" * 5)
        twins = [mutant(2, "Survived", column=11), mutant(4, "Survived", column=11)]
        self.assertEqual(gate.mutant_key(self.repo, twins[0])[0], gate.mutant_key(self.repo, twins[1])[0])
        result = self.judge({WALLET_PATH: "all"}, twins + [mutant(3, "Killed", column=11)],
                            [self.decision(twins[0])])
        self.assertEqual(len(result["unresolved"]), 2)
        self.assertIn("구분할 수 없다", result["unresolved"][0]["hint"])

    def test_decision_with_mismatched_line_text_does_not_resolve(self):
        m = mutant(5, "Survived")
        result = self.judge({WALLET_PATH: [5]}, [m], [self.decision(m, line_text="다른 줄")])
        self.assertEqual(result["verdict"], "fail")

    def test_malformed_decisions_file_is_incomplete(self):
        tmp = os.path.join(self.repo, "decisions.json")
        for content in ({"decisions": {"key": "x"}}, {"version": 1}, [1]):
            write_json(tmp, content)
            with self.assertRaises(gate.IncompleteError):
                gate.load_decisions(tmp)

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

    def check_cli(self, status, extra_reports=True):
        # verify 는 run 결과만 인정하므로 가짜 도구로 run 을 돌린다. 보고서 없이 판정하는 경우만 judge
        if not extra_reports:
            return gate.main(["judge", "--config", self.config_path, "--repo", self.repo.path,
                              "--out", self.result_path])
        fake = os.path.join(self.outside.name, "fake_tool.py")
        with open(fake, "w", encoding="utf-8") as handle:
            handle.write(FAKE_TOOL)
        config = base_config()
        config["modules"][0]["fingerprint"] = ["Packages/Wallet/Package.swift"]
        config["tool"]["command"] = [sys.executable, fake, "{report}", status]
        write_json(self.config_path, config)
        return gate.main(["run", "--config", self.config_path, "--repo", self.repo.path,
                          "--out", self.result_path, "--work-dir", os.path.join(self.outside.name, "work")])

    def verify_cli(self):
        return gate.main(["verify", "--config", self.config_path, "--repo", self.repo.path,
                          "--result", self.result_path])

    def test_pass_then_verify_passes(self):
        self.assertEqual(self.check_cli("Killed"), gate.EXIT_PASS)
        self.assertEqual(self.verify_cli(), gate.EXIT_PASS)

    def test_survivor_fails_and_verify_reports_fail(self):
        self.assertEqual(self.check_cli("Survived"), gate.EXIT_UNRESOLVED)
        self.assertEqual(self.verify_cli(), gate.EXIT_UNRESOLVED)

    def test_test_edit_after_check_makes_result_stale(self):
        self.check_cli("Killed")
        self.repo.write("Packages/Wallet/Tests/WalletTests/WalletTests.swift", WALLET_TEST + "// weaker\n")
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_decision_edit_after_check_makes_result_stale(self):
        self.check_cli("Killed")
        write_json(os.path.join(self.repo.path, ".test-quality/decisions.json"), {"decisions": []})
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_commit_rewrite_without_content_change_stays_valid(self):
        self.check_cli("Killed")
        self.repo.git("commit", "-q", "--amend", "-m", "reworded")
        self.assertEqual(self.verify_cli(), gate.EXIT_PASS)

    def test_missing_result_is_incomplete(self):
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_judge_result_is_not_accepted_by_verify(self):
        # judge 는 보고서만 읽어 판정한다. 손으로 만든 보고서로 통과를 만들 수 있으므로 verify 가 받지 않는다
        write_json(self.report_path, stryker_report("Sources/Wallet/Wallet.swift", [(5, "ROR", ">", "Killed")]))
        code = gate.main(["judge", "--config", self.config_path, "--repo", self.repo.path,
                          "--out", self.result_path, "--report", f"Wallet={self.report_path}"])
        self.assertEqual(code, gate.EXIT_PASS)
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_change_during_run_is_incomplete(self):
        self.assertEqual(self.check_cli("edit"), gate.EXIT_INCOMPLETE)
        with open(self.result_path, encoding="utf-8") as handle:
            self.assertIn("검사 도중", handle.read())

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

    def test_unmapped_report_key_is_incomplete(self):
        write_json(self.report_path, stryker_report("ain/Wallet.swift", [(5, "ROR", ">", "Survived")]))
        args = ["judge", "--config", self.config_path, "--repo", self.repo.path, "--out", self.result_path,
                "--report", f"Wallet={self.report_path}"]
        self.assertEqual(gate.main(args), gate.EXIT_INCOMPLETE)
        with open(self.result_path, encoding="utf-8") as handle:
            self.assertIn("연결할 수 없습니다: ain/Wallet.swift", handle.read())

    def test_ignored_file_report_is_not_mixed_into_target(self):
        # 검사 제외 파일의 결과가 이름이 같은 검사 대상 파일로 연결되면 거짓 통과가 된다
        config = base_config()
        config["ignore"] = ["**/Generated/**"]
        write_json(self.config_path, config)
        self.repo.write("Packages/Wallet/Sources/Wallet/Generated/Wallet.swift", WALLET)
        self.repo.commit("generated")
        write_json(self.report_path, stryker_report("Sources/Wallet/Generated/Wallet.swift",
                                                    [(5, "ROR", ">", "Killed")]))
        args = ["judge", "--config", self.config_path, "--repo", self.repo.path, "--out", self.result_path,
                "--report", f"Wallet={self.report_path}"]
        self.assertNotEqual(gate.main(args), gate.EXIT_PASS)

    def tool_config_judge(self, decisions=None):
        config = base_config()
        config["tool"]["config_files"] = [".swift-mutation-testing.yml"]
        config["ignore"] = ["**/*.yml"]  # 제외 패턴에 걸려도 빠지지 않아야 한다
        write_json(self.config_path, config)
        if decisions is not None:
            write_json(os.path.join(self.repo.path, ".test-quality/decisions.json"), {"decisions": decisions})
        write_json(self.report_path, stryker_report("Sources/Wallet/Wallet.swift", [(5, "ROR", ">", "Killed")]))
        code = gate.main(["judge", "--config", self.config_path, "--repo", self.repo.path,
                          "--out", self.result_path, "--report", f"Wallet={self.report_path}"])
        with open(self.result_path, encoding="utf-8") as handle:
            return code, json.load(handle)

    def test_tool_config_change_needs_approval(self):
        # 실측 시나리오: yml 에 변이 종류 끄기를 넣어도 결과에 흔적이 없어 통과했다
        self.repo.write("Packages/Wallet/.swift-mutation-testing.yml", "timeout: 60\n")
        self.repo.commit("yml base")
        self.repo.git("branch", "-f", "main", "HEAD")
        self.repo.write(WALLET_PATH, WALLET.replace("amount >= 1", "amount >= 2"))
        self.repo.write("Packages/Wallet/.swift-mutation-testing.yml",
                        "timeout: 60\ndisabled-mutators: [RelationalOperatorReplacement]\n")
        self.repo.commit("narrow")
        code, result = self.tool_config_judge()
        self.assertEqual(code, gate.EXIT_UNRESOLVED)
        item = result["unresolved"][0]
        self.assertEqual((item["file"], item["start_line"], item["status"]),
                         ("Packages/Wallet/.swift-mutation-testing.yml", 2, "Ignored"))
        entry = {"key": item["key"], "file": item["file"], "line_text": item["line_text"],
                 "kind": "ignore_approved", "reason": "느린 변이 종류를 끈다", "approved_by": "reviewer"}
        code, _ = self.tool_config_judge([entry])
        self.assertEqual(code, gate.EXIT_PASS)
        # 모듈 fingerprint 에 적지 않아도 도구 설정 파일은 결과에 묶인다
        self.repo.write("Packages/Wallet/.swift-mutation-testing.yml", "timeout: 1\n")
        self.assertEqual(self.verify_cli(), gate.EXIT_INCOMPLETE)

    def test_tool_config_only_change_is_not_not_applicable(self):
        self.repo.git("branch", "-f", "main", "HEAD")
        self.repo.write("Packages/Wallet/.swift-mutation-testing.yml", "disabled-mutators: [X]\n")
        self.repo.commit("yml only")
        code, result = self.tool_config_judge()
        self.assertEqual((code, result["verdict"]), (gate.EXIT_UNRESOLVED, "fail"))

    def test_module_in_scope_without_report_is_incomplete(self):
        self.assertEqual(self.check_cli("Killed", extra_reports=False), gate.EXIT_INCOMPLETE)
        with open(self.result_path, encoding="utf-8") as handle:
            self.assertIn("변이 결과가 없습니다", handle.read())


FAKE_TOOL = r'''
import json, sys, time
report, mode = sys.argv[1], sys.argv[2]
if mode == "edit":  # 검사 도중 소스가 바뀌는 경우
    with open("Sources/Wallet/Wallet.swift", "a") as handle:
        handle.write("// edited\n")
    mode = "Killed"
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

    def test_unrunnable_command_is_incomplete_not_a_crash(self):
        # 실측: 도구 경로에 파일 아래 경로를 주면 NotADirectoryError 로 멈추고 exit 1(미해결과 같음)이었다
        code, result = self.run_gate("Killed", baseline=(os.path.join(self.fake, "x"),))
        self.assertEqual((code, result["verdict"]), (gate.EXIT_INCOMPLETE, "incomplete"))

    def test_non_utf8_tool_output_does_not_crash(self):
        code, _ = self.run_gate("Killed", baseline=(sys.executable, "-c",
                                                    "import sys; sys.stdout.buffer.write(bytes([255, 254]))"))
        self.assertEqual(code, gate.EXIT_PASS)

    def test_unexpected_error_still_writes_incomplete_result(self):
        from unittest import mock
        write_json(self.result_path, {"verdict": "pass", "produced_by": "run"})  # 이전 실행의 통과 결과
        with mock.patch.object(gate, "plan_scope", side_effect=RuntimeError("boom")):
            code, result = self.run_gate("Killed")
        self.assertEqual((code, result["verdict"]), (gate.EXIT_INCOMPLETE, "incomplete"))
        self.assertIn("RuntimeError", result["incomplete_reasons"][0])

    def test_tool_timeout_is_incomplete(self):
        code, _ = self.run_gate("sleep", timeout=1)
        self.assertEqual(code, gate.EXIT_INCOMPLETE)


PROTECT_HOOK = os.path.join(_HERE, "..", "deploy", "hooks", "check_test_quality_protect.py")


class ProtectHookTests(unittest.TestCase):
    # 판단 기록·설정·결과를 AI 가 고치려 하면 허락을 받는지 실제 훅 프로세스로 확인한다
    def decision_of(self, tool_name, tool_input, cwd="/app"):
        payload = {"tool_name": tool_name, "tool_input": tool_input, "cwd": cwd}
        proc = subprocess.run([sys.executable, PROTECT_HOOK], input=json.dumps(payload),
                              capture_output=True, text=True, check=True)
        if not proc.stdout.strip():
            return None
        return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]

    def test_editing_decisions_asks(self):
        self.assertEqual(self.decision_of("Edit", {"file_path": "/app/.test-quality/decisions.json"}), "ask")

    def test_writing_result_asks(self):
        self.assertEqual(self.decision_of("Write", {"file_path": "/app/.test-quality/result.json"}), "ask")

    def test_editing_other_files_passes(self):
        self.assertIsNone(self.decision_of("Edit", {"file_path": "/app/Sources/Wallet.swift"}))

    def test_reading_is_not_blocked(self):
        self.assertIsNone(self.decision_of("Read", {"file_path": "/app/.test-quality/decisions.json"}))

    def test_standalone_gate_run_passes(self):
        command = ("python3 ~/.claude/skills/test-quality/scripts/mutation_gate.py run "
                   "--config .test-quality/config.json --out .test-quality/result.json")
        self.assertIsNone(self.decision_of("Bash", {"command": command}))

    def test_gate_run_chained_with_write_asks(self):
        command = ("python3 mutation_gate.py run --config .test-quality/config.json --out r.json; "
                   "echo '{}' > .test-quality/decisions.json")
        self.assertEqual(self.decision_of("Bash", {"command": command}), "ask")

    def test_shell_write_to_tool_config_asks(self):
        command = "printf 'disabled-mutators: [RelationalOperatorReplacement]' > .swift-mutation-testing.yml"
        self.assertEqual(self.decision_of("Bash", {"command": command}), "ask")

    def test_common_gate_output_handling_passes(self):
        # 게이트는 오래 걸려 출력을 돌리기 쉽다 — 보호 경로가 아닌 곳으로의 리다이렉트·파이프는 묻지 않는다
        gate_run = "python3 mutation_gate.py run --config .test-quality/config.json --out .test-quality/result.json"
        for command in (gate_run + " 2>&1 | tail -n 80", gate_run + " > /tmp/tq.log 2>&1",
                        "python3 mutation_gate.py verify --config .test-quality/config.json "
                        "--result .test-quality/result.json"):
            self.assertIsNone(self.decision_of("Bash", {"command": command}), command)

    def test_gate_judge_is_not_exempt(self):
        command = ("python3 mutation_gate.py judge --config .test-quality/config.json "
                   "--report Wallet=hand.json --out .test-quality/result.json")
        self.assertEqual(self.decision_of("Bash", {"command": command}), "ask")

    def test_read_only_and_staging_commands_pass(self):
        for command in ("git add .test-quality/decisions.json", "git -C /app add .test-quality/decisions.json",
                        "cat .test-quality/result.json > /tmp/r.json", "git diff -- .test-quality",
                        "grep -n key .test-quality/decisions.json | head"):
            self.assertIsNone(self.decision_of("Bash", {"command": command}), command)

    def test_description_is_not_inspected(self):
        payload = {"command": "git status", "description": "Check .test-quality/result.json staging"}
        self.assertIsNone(self.decision_of("Bash", payload))

    def test_indirect_shell_writes_ask(self):
        # 리뷰 재현: 폴더 지정·cd·코드로 만든 경로·git 복원
        for command in ("cp /tmp/d.json .test-quality/", "mv /tmp/draft/config.json .test-quality/",
                        "cd .test-quality && sed -i '' s/a/b/ decisions.json",
                        "python3 -c \"import pathlib; (pathlib.Path('.test-quality')/'decisions.json').write_text('x')\"",
                        "python3 - <<'EOF'\nimport os\nopen(os.path.join('.test-quality', 'decisions.json'), 'w')\nEOF",
                        "git checkout origin/main -- .test-quality", "echo x | tee .test-quality/decisions.json",
                        "git show main:x > .test-quality/decisions.json"):
            self.assertEqual(self.decision_of("Bash", {"command": command}), "ask", command)

    def test_shell_inside_protected_dir_asks(self):
        self.assertEqual(self.decision_of("Bash", {"command": "sed -i '' s/a/b/ decisions.json"},
                                          cwd="/app/.test-quality"), "ask")
        self.assertIsNone(self.decision_of("Bash", {"command": "cat decisions.json"}, cwd="/app/.test-quality"))

    def test_monitor_command_is_inspected(self):
        command = "cp /tmp/d.json .test-quality/decisions.json; echo done"
        self.assertEqual(self.decision_of("Monitor", {"command": command}), "ask")

    def test_codex_patch_checks_only_file_headers(self):
        # Codex apply_patch 는 패치 본문 전체를 command 로 보낸다. 본문에 경로가 나온다고 막으면 안 된다
        gitignore = "*** Begin Patch\n*** Update File: .gitignore\n@@\n+.test-quality/result.json\n*** End Patch"
        self.assertIsNone(self.decision_of("apply_patch", {"command": gitignore}))
        decisions = "*** Begin Patch\n*** Update File: .test-quality/decisions.json\n@@\n-a\n+b\n*** End Patch"
        self.assertEqual(self.decision_of("apply_patch", {"command": decisions}), "ask")

    def test_ci_workflow_is_protected(self):
        # continue-on-error 를 넣으면 미해결이 있어도 필수 상태 검사가 초록이 된다
        self.assertEqual(self.decision_of("Edit", {"file_path": "/app/.github/workflows/test-quality.yml"}), "ask")

    def test_other_tools_are_not_inspected(self):
        plan = {"plan": [{"step": "fill .test-quality/decisions.json", "status": "pending"}]}
        self.assertIsNone(self.decision_of("update_plan", plan))


if __name__ == "__main__":
    unittest.main(verbosity=1)
