#!/usr/bin/env python3
# 변이 검사 게이트 — 바뀐 로직에 변이 도구를 돌리고, 결과를 공통 기준으로 판정한다.
#
# 판정 기준의 단일 출처는 contexts/testing-strategy/test-quality.md 다. 이 실행기는 그 기준을
# 기계로 강제한다: 미해결 0건이어야 통과, 도구 오류·결과 누락·오래된 결과는 성공으로 처리하지 않는다.
#
# 도구에 묶이지 않는다. 도구 명령은 프로젝트 설정이 공급하고, 결과는 Stryker 보고서 형식
# (mutation-testing-report-schema)으로 읽는다. 표준 라이브러리만 쓴다 — 앱 CI 에서 그대로 돈다.
#
# 종료 코드: 0 통과·해당 없음 / 1 미해결 있음 / 2 검사 미완료 / 3 설정·사용 오류
import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

RUNNER_VERSION = "0.1.0"

EXIT_PASS = 0
EXIT_UNRESOLVED = 1
EXIT_INCOMPLETE = 2
EXIT_USAGE = 3


class ConfigError(Exception):
    pass


class IncompleteError(Exception):
    # git·도구 실행이 실패해 판정할 근거가 없는 경우. 통과로 처리하지 않는다.
    pass


_PLACEHOLDER = re.compile(r"\{([a-z_]+(?::[A-Za-z0-9_]+)?)\}")


def expand(template, values):
    # "{name}" 은 values 에서, "{env:NAME}" 은 환경변수에서 채운다. 못 채우면 설정 오류 —
    # 빈 문자열로 넘기면 도구가 엉뚱한 대상을 돌고도 성공할 수 있다.
    def replace(match):
        key = match.group(1)
        if key.startswith("env:"):
            name = key[4:]
            if name not in os.environ:
                raise ConfigError(f"환경변수 {name} 가 없습니다 ({template})")
            return os.environ[name]
        if key not in values:
            raise ConfigError(f"자리표시자 {{{key}}} 를 채울 값이 없습니다 ({template})")
        return expand(str(values[key]), values)

    return _PLACEHOLDER.sub(replace, template)


def _require(obj, key, kind, where):
    if key not in obj:
        raise ConfigError(f"{where}.{key} 가 없습니다")
    if not isinstance(obj[key], kind):
        raise ConfigError(f"{where}.{key} 형식이 맞지 않습니다")
    return obj[key]


def _norm_dir(path):
    return path.strip("/").replace("\\", "/")


def _check_command(command, where):
    if not command or not all(isinstance(part, str) for part in command):
        raise ConfigError(f"{where} 는 문자열 목록이어야 합니다")
    if "{report}" not in " ".join(command):
        raise ConfigError(f"{where} 에 {{report}} 자리표시자가 있어야 합니다")


def load_config(path):
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as error:
        raise ConfigError(f"설정 파일을 읽을 수 없습니다: {error}")
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ConfigError(f"설정 파일이 JSON 이 아닙니다: {error}")
    if not isinstance(config, dict):
        raise ConfigError("설정 최상위는 객체여야 합니다")
    if config.get("version") != 1:
        raise ConfigError("version 은 1 이어야 합니다")

    _require(config, "base", str, "config")
    extensions = _require(config, "source_extensions", list, "config")
    if not extensions or not all(isinstance(e, str) and e.startswith(".") for e in extensions):
        raise ConfigError("config.source_extensions 는 '.swift' 같은 확장자 목록이어야 합니다")
    config.setdefault("ignore", [])
    config.setdefault("decisions", ".test-quality/decisions.json")

    tool = _require(config, "tool", dict, "config")
    for key in ("name", "version"):
        _require(tool, key, str, "config.tool")
    _check_command(_require(tool, "command", list, "config.tool"), "config.tool.command")
    tool.setdefault("timeout_seconds", 7200)

    modules = _require(config, "modules", list, "config")
    if not modules:
        raise ConfigError("config.modules 가 비어 있습니다")
    names = set()
    for index, module in enumerate(modules):
        where = f"config.modules[{index}]"
        if not isinstance(module, dict):
            raise ConfigError(f"{where} 는 객체여야 합니다")
        name = _require(module, "name", str, where)
        if name in names:
            raise ConfigError(f"모듈 이름 {name} 가 중복됩니다")
        names.add(name)
        module["path"] = _norm_dir(_require(module, "path", str, where))
        for key in ("sources", "tests"):
            dirs = _require(module, key, list, where)
            if not dirs:
                raise ConfigError(f"{where}.{key} 가 비어 있습니다")
            module[key] = [_norm_dir(d) for d in dirs]
        baseline = _require(module, "baseline", list, where)
        if not baseline or not all(isinstance(part, str) for part in baseline):
            raise ConfigError(f"{where}.baseline 은 문자열 목록이어야 합니다")
        if "command" in module:
            # 한 앱에 시뮬레이터 모듈과 호스트(macOS) 모듈이 섞이면 도구 인자가 다르다
            _check_command(module["command"], f"{where}.command")
        module.setdefault("vars", {})
        module.setdefault("fingerprint", [])
    return config


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise IncompleteError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout


_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_diff(text):
    # unified diff(-U0) → {새 경로: 바뀐 줄 번호 집합}. 삭제된 파일은 빈 집합으로 남긴다.
    # 줄만 지운 자리(+c,0)는 새 줄이 없으므로 앞뒤 줄을 대상으로 본다 — 조건 한 줄을 지운
    # 변경도 그 주변 로직의 검사로 이어지게 한다.
    changes = {}
    old_path = None
    current = None
    for line in text.splitlines():
        if line.startswith("--- "):
            old_path = line[4:]
            old_path = old_path[2:] if old_path.startswith("a/") else old_path
            continue
        if line.startswith("+++ "):
            new_path = line[4:]
            if new_path == "/dev/null":
                current = None
                changes.setdefault(old_path, set())
            else:
                current = new_path[2:] if new_path.startswith("b/") else new_path
                changes.setdefault(current, set())
            continue
        match = _HUNK.match(line)
        if match and current is not None:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            if count == 0:
                changes[current].update(n for n in (start, start + 1) if n > 0)
            else:
                changes[current].update(range(start, start + count))
    return changes


def _under(path, dirs):
    return any(path == d or path.startswith(d + "/") for d in dirs)


def _ignored(path, patterns):
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _is_logic(path, config):
    return os.path.splitext(path)[1] in config["source_extensions"]


def _module_logic_files(repo, module, config):
    files = []
    for source_dir in module["sources"]:
        root = os.path.join(repo, source_dir)
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.relpath(os.path.join(dirpath, filename), repo).replace(os.sep, "/")
                if _is_logic(path, config) and not _ignored(path, config["ignore"]):
                    files.append(path)
    return sorted(files)


def plan_scope(repo, config, base=None):
    # 기준 브랜치 대비 바뀐 내용으로 모듈별 검사 범위를 정한다. 작업 트리의 미커밋 변경과
    # 추적 안 된 새 파일도 포함한다 — 커밋 전 로컬 검사에서 새 파일이 빠지면 안 된다.
    base = base or config["base"]
    merge_base = git(repo, "merge-base", "HEAD", base).strip()
    changes = parse_diff(git(repo, "diff", "-U0", "-M", "--no-color", merge_base))
    for path in git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
        if path:
            changes[path] = None  # None = 파일 전체

    modules = {
        m["name"]: {"targets": {}, "widened": False, "source_changed": [], "test_changed": []}
        for m in config["modules"]
    }
    plan = {"merge_base": merge_base, "changed": sorted(changes), "modules": modules,
            "unmapped": [], "ignored": [], "other": []}

    for path in sorted(changes):
        if _ignored(path, config["ignore"]):
            plan["ignored"].append(path)
            continue
        owner = None
        role = None
        for module in config["modules"]:
            if _under(path, module["sources"]):
                owner, role = module, "source"
            elif _under(path, module["tests"]):
                owner, role = module, "test"
            elif path in module["fingerprint"]:
                owner, role = module, "manifest"
            if owner:
                break
        if owner is None:
            (plan["unmapped"] if _is_logic(path, config) else plan["other"]).append(path)
            continue
        entry = modules[owner["name"]]
        if role == "test":
            entry["test_changed"].append(path)
        elif role == "source":
            entry["source_changed"].append(path)
            exists = os.path.exists(os.path.join(repo, path))
            if _is_logic(path, config) and exists:
                lines = changes[path]
                if lines is None:
                    entry["targets"][path] = "all"
                elif lines:
                    entry["targets"][path] = sorted(lines)

    for module in config["modules"]:
        entry = modules[module["name"]]
        if entry["test_changed"] and not entry["source_changed"]:
            entry["widened"] = True
            entry["targets"] = {path: "all" for path in _module_logic_files(repo, module, config)}
    return plan


STRYKER_STATUSES = {
    "Killed", "Survived", "NoCoverage", "Timeout", "RuntimeError", "CompileError", "Ignored", "Pending",
}


def _components(path):
    return [part for part in path.replace("\\", "/").split("/") if part and part != "."]


def resolve_report_path(key, repo, roots, known_files):
    # 보고서의 파일 키를 저장소 기준 상대 경로로 바꾼다. 도구마다 절대 경로·프로젝트 기준·잘린
    # 경로(심볼릭 링크 경로 길이 차로 앞이 잘리는 도구 버그 실측)가 섞여 있어, 실제 파일 목록과
    # 경로 끝부분이 가장 길게 일치하는 것을 고른다. 동률이면 판정하지 않는다(None).
    real_repo = os.path.realpath(repo)
    candidates = []
    if os.path.isabs(key):
        candidates.append(os.path.realpath(key))
    for root in roots:
        if root:
            candidates.append(os.path.realpath(os.path.join(root, key)))
    for candidate in candidates:
        rel = os.path.relpath(candidate, real_repo).replace(os.sep, "/")
        if rel in known_files:
            return rel

    key_parts = _components(key)
    best, best_len, tie = None, 0, False
    for rel in known_files:
        rel_parts = _components(rel)
        common = 0
        while (common < len(key_parts) and common < len(rel_parts)
               and key_parts[-1 - common] == rel_parts[-1 - common]):
            common += 1
        if common > best_len:
            best, best_len, tie = rel, common, False
        elif common == best_len and common > 0:
            tie = True
    if best is None or tie:
        return None
    return best


def load_report(path, repo, roots, known_files):
    # Stryker 보고서(mutation-testing-report-schema) → 변이 목록. 읽을 수 없거나 형식이 다르면
    # 판정 근거가 없으므로 미완료다.
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise IncompleteError(f"결과 파일이 없습니다: {path}")
    except (OSError, json.JSONDecodeError) as error:
        raise IncompleteError(f"결과 파일을 읽을 수 없습니다: {path} ({error})")
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict):
        raise IncompleteError(f"결과 형식 불일치(files 없음): {path}")

    mutants, unresolved_keys = [], []
    for key, entry in files.items():
        rel = resolve_report_path(key, repo, roots + [data.get("projectRoot")], known_files)
        if rel is None:
            unresolved_keys.append(key)
            continue
        for raw in entry.get("mutants", []) if isinstance(entry, dict) else []:
            status = raw.get("status")
            if status not in STRYKER_STATUSES:
                raise IncompleteError(f"알 수 없는 변이 상태 {status!r}: {path}")
            try:
                start = raw["location"]["start"]
                end = raw["location"]["end"]
                mutants.append({
                    "file": rel,
                    "start_line": int(start["line"]),
                    "start_column": int(start["column"]),
                    "end_line": int(end["line"]),
                    "mutator": str(raw["mutatorName"]),
                    "original": str(raw.get("originalText", "")),
                    "replacement": str(raw.get("replacement", "")),
                    "status": status,
                })
            except (KeyError, TypeError, ValueError):
                raise IncompleteError(f"변이 항목 형식 불일치: {path}")
    return mutants, unresolved_keys


# 판단 기록 종류 → 그 기록으로 해소할 수 있는 상태. 종류와 상태가 맞지 않으면 해소하지 않는다.
DECISION_KINDS = {
    "equivalent": {"Survived", "NoCoverage"},
    "hang_detected": {"Timeout"},
    "crash_detected": {"RuntimeError"},
    "ignore_approved": {"Ignored"},
}

HINTS = {
    "Survived": "요구사항과 대조해 테스트 누락·약한 단언인지 판단하고 보강한다",
    "NoCoverage": "이 지점을 실행하는 테스트를 보강한다",
    "Timeout": "제한 시간을 늘려 다시 돌리거나, 변이가 무한 반복을 만든 근거를 판단 기록으로 남긴다",
    "RuntimeError": "다시 돌려도 같으면 근거를 판단 기록으로 남긴다",
    "Ignored": "제외 주석·설정을 걷어내거나, 승인된 판단 기록을 남긴다",
}

# 바뀐 줄에 이런 연산자가 보이는데 그 파일 변이가 하나도 없으면, 도구가 파일을 분석했다는
# 근거가 없다고 본다. Swift·Dart 공통 표기만 쓴다.
_MUTABLE_TOKEN = re.compile(r"==|!=|>=|<=|&&|\|\|| > | < |\btrue\b|\bfalse\b")


def _read_lines(repo, rel):
    try:
        with open(os.path.join(repo, rel), encoding="utf-8") as handle:
            return handle.read().splitlines()
    except OSError:
        return []


def mutant_key(repo, mutant, cache=None):
    # 판단 기록을 줄 번호가 아니라 원래 줄 내용에 묶는다. 위쪽 코드가 바뀌어 줄 번호가 밀려도
    # 기록이 따라가고, 그 줄 자체가 바뀌면 기록이 떨어져 다시 판단하게 된다.
    if cache is not None and mutant["file"] in cache:
        lines = cache[mutant["file"]]
    else:
        lines = _read_lines(repo, mutant["file"])
        if cache is not None:
            cache[mutant["file"]] = lines
    index = mutant["start_line"] - 1
    text = lines[index] if 0 <= index < len(lines) else ""
    stripped = text.strip()
    column = mutant["start_column"] - (len(text) - len(text.lstrip()))
    raw = "\0".join([mutant["file"], stripped, str(column), mutant["mutator"], mutant["replacement"]])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], stripped


def load_decisions(path):
    # 판단 기록 파일. 없으면 빈 목록. 형식이 틀린 항목은 쓰지 않고 따로 보고한다 —
    # 근거·승인자 없는 기록이 해소로 새면 "사람만 승인" 기준이 무너진다.
    if not os.path.exists(path):
        return [], []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise IncompleteError(f"판단 기록 파일을 읽을 수 없습니다: {path} ({error})")
    entries = data.get("decisions", []) if isinstance(data, dict) else []
    valid, invalid = [], []
    for entry in entries:
        ok = (isinstance(entry, dict)
              and isinstance(entry.get("key"), str) and entry["key"]
              and entry.get("kind") in DECISION_KINDS
              and isinstance(entry.get("reason"), str) and entry["reason"].strip()
              and isinstance(entry.get("approved_by"), str) and entry["approved_by"].strip())
        (valid if ok else invalid).append(entry)
    return valid, invalid


def _in_scope(mutant, lines):
    if lines == "all":
        return True
    return any(mutant["start_line"] <= n <= mutant["end_line"] for n in lines)


def _code_part(line):
    return line.split("//", 1)[0]


def judge(repo, plan, mutants, module_mutant_counts, decisions, skip_modules=()):
    # 계획된 범위와 변이 결과를 test-quality.md 「상태별 판정」으로 판정한다.
    # skip_modules: 결과 자체가 없어 호출자가 이미 미완료 사유를 남긴 모듈 (사유를 겹쳐 쓰지 않는다).
    by_key = {d["key"]: d for d in decisions}
    used_keys = set()
    cache = {}
    result = {"detected": [], "unresolved": [], "resolved": [], "invalid_mutants": 0,
              "out_of_scope": 0, "no_mutants": [], "incomplete_reasons": []}
    any_target = False

    for path in plan["unmapped"]:
        result["incomplete_reasons"].append(f"검사 설정 밖의 로직 파일이 바뀌었습니다: {path}")

    for name, entry in plan["modules"].items():
        if not entry["targets"]:
            continue
        any_target = True
        if name in skip_modules:
            continue
        if module_mutant_counts.get(name, 0) == 0:
            result["incomplete_reasons"].append(
                f"모듈 {name}: 도구가 변이를 하나도 만들지 않았습니다 — 분석했다는 근거가 없습니다")
            continue
        in_scope_total, compile_errors = 0, 0
        for path, lines in entry["targets"].items():
            file_mutants = [m for m in mutants if m["file"] == path]
            in_scope = [m for m in file_mutants if _in_scope(m, lines)]
            result["out_of_scope"] += len(file_mutants) - len(in_scope)
            if not in_scope:
                source = _read_lines(repo, path)
                numbers = range(1, len(source) + 1) if lines == "all" else lines
                if any(_MUTABLE_TOKEN.search(_code_part(source[n - 1]))
                       for n in numbers if 0 < n <= len(source)):
                    result["incomplete_reasons"].append(
                        f"{path}: 바뀐 줄에 변이할 연산자가 보이는데 결과가 없습니다")
                else:
                    result["no_mutants"].append(path)
                continue
            for mutant in in_scope:
                in_scope_total += 1
                status = mutant["status"]
                key, text = mutant_key(repo, mutant, cache)
                item = dict(mutant, key=key, line_text=text)
                if status == "Killed":
                    result["detected"].append(item)
                elif status == "CompileError":
                    compile_errors += 1
                    result["invalid_mutants"] += 1
                elif status == "Pending":
                    result["incomplete_reasons"].append(f"{path}:{mutant['start_line']} 변이가 실행되지 않았습니다(Pending)")
                else:
                    decision = by_key.get(key)
                    if decision and status in DECISION_KINDS[decision["kind"]]:
                        used_keys.add(key)
                        result["resolved"].append(dict(item, decision=decision))
                    else:
                        result["unresolved"].append(dict(item, hint=HINTS[status]))
        if in_scope_total and in_scope_total == compile_errors:
            result["incomplete_reasons"].append(
                f"모듈 {name}: 범위 안 변이가 모두 컴파일 실패라 실제로 검사한 것이 없습니다")

    result["stale_decisions"] = [d["key"] for d in decisions if d["key"] not in used_keys]
    if result["incomplete_reasons"]:
        result["verdict"] = "incomplete"
    elif result["unresolved"]:
        result["verdict"] = "fail"
    elif not any_target:
        result["verdict"] = "not_applicable"
    else:
        result["verdict"] = "pass"
    return result


def _digest(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except FileNotFoundError:
        return "absent"


def _walk_files(repo, rel_dir):
    root = os.path.join(repo, rel_dir)
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            yield os.path.relpath(os.path.join(dirpath, filename), repo).replace(os.sep, "/")


def fingerprint(repo, config_path, config, plan):
    # 결과를 검사 당시의 소스·테스트·설정·판단 기록 내용에 묶는다. 검사 뒤 하나라도 바뀌면
    # 값이 달라져 이전 결과는 무효가 된다. 커밋 해시가 아니라 내용을 쓰므로 커밋 정리(rebase·
    # squash)만으로는 무효가 되지 않고, 미커밋 수정은 잡는다.
    digest = hashlib.sha256()

    def feed(label, value):
        digest.update(label.encode("utf-8") + b"\0" + value.encode("utf-8") + b"\n")

    feed("runner", RUNNER_VERSION)
    feed("config", _digest(config_path))
    feed("decisions", _digest(os.path.join(repo, config["decisions"])))
    scope = {name: {"targets": e["targets"], "widened": e["widened"]}
             for name, e in plan["modules"].items()}
    feed("scope", json.dumps({"modules": scope, "unmapped": plan["unmapped"]}, sort_keys=True))
    for module in config["modules"]:
        entry = plan["modules"][module["name"]]
        if not (entry["targets"] or entry["source_changed"] or entry["test_changed"]):
            continue
        files = set(module["fingerprint"])
        for rel_dir in module["sources"] + module["tests"]:
            files.update(_walk_files(repo, rel_dir))
        for rel in sorted(files):
            feed(rel, _digest(os.path.join(repo, rel)))
    return digest.hexdigest()


def build_result(config, plan, judged, fingerprint_value):
    def brief(item):
        keys = ("key", "file", "start_line", "start_column", "mutator", "original", "replacement",
                "status", "line_text", "hint")
        return {k: item[k] for k in keys if k in item}

    return {
        "runner_version": RUNNER_VERSION,
        "tool": {"name": config["tool"]["name"], "version": config["tool"]["version"]},
        "verdict": judged["verdict"],
        "fingerprint": fingerprint_value,
        "merge_base": plan["merge_base"],
        "scope": {
            "modules": {name: {"targets": e["targets"], "widened": e["widened"]}
                        for name, e in plan["modules"].items() if e["targets"]},
            "unmapped": plan["unmapped"], "ignored": plan["ignored"], "other": plan["other"],
        },
        "summary": {
            "detected": len(judged["detected"]), "unresolved": len(judged["unresolved"]),
            "resolved_by_decision": len(judged["resolved"]),
            "compile_errors": judged["invalid_mutants"], "out_of_scope": judged["out_of_scope"],
        },
        "unresolved": [brief(m) for m in judged["unresolved"]],
        "resolved": [dict(brief(m), reason=m["decision"]["reason"],
                          approved_by=m["decision"]["approved_by"]) for m in judged["resolved"]],
        "no_mutants": judged["no_mutants"],
        "incomplete_reasons": judged["incomplete_reasons"],
        "invalid_decisions": judged.get("invalid_decisions", 0),
        "stale_decisions": judged["stale_decisions"],
    }


VERDICT_EXIT = {"pass": EXIT_PASS, "not_applicable": EXIT_PASS, "fail": EXIT_UNRESOLVED,
                "incomplete": EXIT_INCOMPLETE}

VERDICT_LABEL = {"pass": "통과 — 범위 안 미해결 0건", "not_applicable": "해당 없음 — 검사할 로직 변경이 없음",
                 "fail": "미해결 있음", "incomplete": "검사 미완료 — 성공으로 처리하지 않는다"}


def print_result(result, out=sys.stdout):
    print(f"[test-quality] {VERDICT_LABEL[result['verdict']]}", file=out)
    summary = result["summary"]
    print(f"  검출 {summary['detected']} · 미해결 {summary['unresolved']} · 판단 기록 해소 "
          f"{summary['resolved_by_decision']} · 컴파일 실패 제외 {summary['compile_errors']} · "
          f"범위 밖 {summary['out_of_scope']}", file=out)
    for reason in result["incomplete_reasons"]:
        print(f"  미완료: {reason}", file=out)
    for item in result["unresolved"]:
        # 한 줄에 같은 종류 연산자가 여럿일 수 있어 원래 표기와 열 번호를 함께 보인다
        change = f"{item.get('original') or '?'} → {item['replacement'] or '(삭제)'}"
        print(f"  미해결 {item['file']}:{item['start_line']}:{item.get('start_column', '?')} "
              f"{item['mutator']} {change} [{item['status']}] key={item['key']}\n"
              f"      {item['line_text']}\n      {item['hint']}", file=out)
    for path in result["no_mutants"]:
        print(f"  변이 지점 없음(해당 없음): {path}", file=out)
    if result["stale_decisions"]:
        print(f"  맞는 변이가 없는 판단 기록: {', '.join(result['stale_decisions'])}", file=out)


def write_result(path, result):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def known_logic_files(repo, config):
    files = []
    for module in config["modules"]:
        files.extend(_module_logic_files(repo, module, config))
    return files


def judge_reports(repo, config_path, config, plan, reports, module_errors=None):
    # reports: {모듈 이름: 결과 파일 경로}. 범위가 있는 모듈의 결과가 없으면 미완료다.
    module_errors = module_errors or {}
    decisions, invalid = load_decisions(os.path.join(repo, config["decisions"]))
    known = known_logic_files(repo, config)
    mutants, counts, extra, missing = [], {}, [], []
    for module in config["modules"]:
        name = module["name"]
        if not plan["modules"][name]["targets"]:
            continue
        if name not in reports:
            extra.append(module_errors.get(name, f"모듈 {name}: 변이 결과가 없습니다"))
            missing.append(name)
            continue
        try:
            loaded, _ = load_report(reports[name], repo, [os.path.join(repo, module["path"])], known)
        except IncompleteError as error:
            # 한 모듈의 결과가 깨져도 결과 파일은 남긴다 — CI 산출물로 사유를 볼 수 있어야 한다
            extra.append(f"모듈 {name}: {error}")
            missing.append(name)
            continue
        mutants.extend(loaded)
        counts[name] = len(loaded)
    judged = judge(repo, plan, mutants, counts, decisions, skip_modules=missing)
    judged["invalid_decisions"] = len(invalid)
    if extra:
        judged["incomplete_reasons"] = extra + judged["incomplete_reasons"]
        judged["verdict"] = "incomplete"
    return build_result(config, plan, judged, fingerprint(repo, config_path, config, plan))


def _run_logged(argv, cwd, timeout, log_path):
    # 명령을 돌리고 출력 전체를 로그로 남긴다. 실행 불가·시간 초과는 판정 근거가 없으므로 미완료.
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise IncompleteError(f"명령을 찾을 수 없습니다: {argv[0]}")
    except subprocess.TimeoutExpired:
        raise IncompleteError(f"{timeout}초 안에 끝나지 않았습니다: {' '.join(argv)}")
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(f"$ {' '.join(argv)}\n(cwd {cwd}, exit {proc.returncode})\n\n")
        handle.write(proc.stdout or "")
        handle.write(proc.stderr or "")
    return proc.returncode


def run_gate(repo, config_path, config, base, work_dir, overrides):
    # 범위 계산 → 모듈별 기준 테스트 → 변이 도구 → 판정. 모듈 하나의 실패가 다른 모듈 결과를
    # 가리지 않도록 실패는 사유로 모아 두고, 판정 단계에서 미완료로 합친다.
    plan = plan_scope(repo, config, base)
    tool = config["tool"]
    reports, errors = {}, {}
    for module in config["modules"]:
        name = module["name"]
        if not plan["modules"][name]["targets"]:
            continue
        module_path = os.path.join(repo, module["path"])
        report = os.path.join(work_dir, f"{name}.stryker.json")
        values = dict(module["vars"])
        values.update(overrides)
        values.update({"repo": repo, "module_path": module_path, "report": report,
                       "sources_path": os.path.join(repo, module["sources"][0])})
        try:
            baseline = [expand(part, values) for part in module["baseline"]]
            command = [expand(part, values) for part in module.get("command", tool["command"])]
            code = _run_logged(baseline, module_path, tool["timeout_seconds"],
                               os.path.join(work_dir, f"{name}.baseline.log"))
            if code != 0:
                errors[name] = f"모듈 {name}: 변이 전 기준 테스트가 실패했습니다 (exit {code})"
                continue
            if os.path.exists(report):
                os.remove(report)  # 이전 실행의 결과를 이번 결과로 읽지 않는다
            code = _run_logged(command, module_path, tool["timeout_seconds"],
                               os.path.join(work_dir, f"{name}.tool.log"))
            if code != 0:
                errors[name] = f"모듈 {name}: 변이 도구가 실패했습니다 (exit {code})"
                continue
            if not os.path.exists(report):
                errors[name] = f"모듈 {name}: 변이 도구가 결과 파일을 만들지 않았습니다"
                continue
            reports[name] = report
        except IncompleteError as error:
            errors[name] = f"모듈 {name}: {error}"
    return judge_reports(repo, config_path, config, plan, reports, errors)


def verify(repo, config_path, config, result_path, base=None):
    # 저장된 결과가 지금 코드에 대해 유효한 통과인지 확인한다. 결과 없음·오래된 결과는 미완료.
    if not os.path.exists(result_path):
        return EXIT_INCOMPLETE, "결과 파일이 없습니다 — 검사를 실행하지 않았습니다"
    try:
        with open(result_path, encoding="utf-8") as handle:
            result = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return EXIT_INCOMPLETE, f"결과 파일을 읽을 수 없습니다 ({error})"
    plan = plan_scope(repo, config, base)
    current = fingerprint(repo, config_path, config, plan)
    if result.get("fingerprint") != current:
        return EXIT_INCOMPLETE, "결과가 오래됐습니다 — 검사 뒤 코드·테스트·설정·판단 기록이 바뀌었습니다"
    verdict = result.get("verdict")
    if verdict not in VERDICT_EXIT:
        return EXIT_INCOMPLETE, f"알 수 없는 판정 {verdict!r}"
    return VERDICT_EXIT[verdict], VERDICT_LABEL[verdict]


def _parse_reports(values):
    reports = {}
    for value in values or []:
        name, sep, path = value.partition("=")
        if not sep or not name or not path:
            raise ConfigError(f"--report 는 모듈=경로 형식이어야 합니다: {value}")
        reports[name] = os.path.abspath(path)
    return reports


def main(argv=None):
    parser = argparse.ArgumentParser(description="변이 검사 게이트")
    parser.add_argument("--version", action="version", version=RUNNER_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-config", help="설정 파일만 검증한다")
    check.add_argument("--config", required=True)
    plan_parser = sub.add_parser("plan", help="검사 범위만 계산해 출력한다 (도구를 돌리지 않는다)")
    plan_parser.add_argument("--config", required=True)
    plan_parser.add_argument("--repo", default=".")
    plan_parser.add_argument("--base")
    judge_parser = sub.add_parser("judge", help="이미 만든 변이 결과(Stryker 형식)를 판정해 결과 파일을 쓴다")
    judge_parser.add_argument("--config", required=True)
    judge_parser.add_argument("--repo", default=".")
    judge_parser.add_argument("--base")
    judge_parser.add_argument("--report", action="append", metavar="모듈=경로")
    judge_parser.add_argument("--out", required=True)
    run_parser = sub.add_parser("run", help="기준 테스트 → 변이 도구 → 판정을 돌리고 결과 파일을 쓴다")
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--repo", default=".")
    run_parser.add_argument("--base")
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--work-dir", help="도구 결과·로그를 둘 폴더 (기본: 임시 폴더)")
    run_parser.add_argument("--var", action="append", metavar="이름=값",
                            help="모듈 vars 덮어쓰기 (예: destination=platform=iOS Simulator,id=...)")
    verify_parser = sub.add_parser("verify", help="저장된 결과가 지금 코드에 대해 유효한 통과인지 확인한다")
    verify_parser.add_argument("--config", required=True)
    verify_parser.add_argument("--repo", default=".")
    verify_parser.add_argument("--base")
    verify_parser.add_argument("--result", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "check-config":
            load_config(args.config)
            print("설정 정상")
            return EXIT_PASS
        if args.command == "plan":
            config = load_config(args.config)
            print(json.dumps(plan_scope(os.path.abspath(args.repo), config, args.base),
                             ensure_ascii=False, indent=2))
            return EXIT_PASS
        if args.command == "judge":
            repo = os.path.abspath(args.repo)
            config = load_config(args.config)
            plan = plan_scope(repo, config, args.base)
            result = judge_reports(repo, os.path.abspath(args.config), config, plan,
                                   _parse_reports(args.report))
            write_result(args.out, result)
            print_result(result)
            return VERDICT_EXIT[result["verdict"]]
        if args.command == "run":
            repo = os.path.abspath(args.repo)
            config = load_config(args.config)
            overrides = {}
            for value in args.var or []:
                name, sep, val = value.partition("=")
                if not sep or not name:
                    raise ConfigError(f"--var 는 이름=값 형식이어야 합니다: {value}")
                overrides[name] = val
            work_dir = os.path.abspath(args.work_dir) if args.work_dir else tempfile.mkdtemp(prefix="test-quality-")
            os.makedirs(work_dir, exist_ok=True)
            result = run_gate(repo, os.path.abspath(args.config), config, args.base, work_dir, overrides)
            result["work_dir"] = work_dir
            write_result(args.out, result)
            print_result(result)
            print(f"  도구 결과·로그: {work_dir}")
            return VERDICT_EXIT[result["verdict"]]
        if args.command == "verify":
            repo = os.path.abspath(args.repo)
            config = load_config(args.config)
            code, message = verify(repo, os.path.abspath(args.config), config, args.result, args.base)
            print(f"[test-quality] {message}")
            return code
    except ConfigError as error:
        print(f"설정 오류: {error}", file=sys.stderr)
        return EXIT_USAGE
    except IncompleteError as error:
        print(f"검사 미완료: {error}", file=sys.stderr)
        return EXIT_INCOMPLETE
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
