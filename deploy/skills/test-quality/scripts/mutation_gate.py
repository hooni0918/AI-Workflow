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

DECISIONS_PATH = ".test-quality/decisions.json"


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


def _string_list(obj, key, where, default=None):
    # 경로·패턴 목록. 문자열 하나를 목록 대신 쓰면 글자 단위로 풀려 범위가 조용히 틀어진다.
    if key not in obj and default is not None:
        obj[key] = list(default)
    value = _require(obj, key, list, where)
    if not all(isinstance(item, str) and item for item in value):
        raise ConfigError(f"{where}.{key} 는 비어 있지 않은 문자열 목록이어야 합니다")
    return value


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
    _string_list(config, "ignore", "config", default=[])
    # 판단 기록 위치는 고정한다 — 보호 훅·CODEOWNERS 가 지키는 .test-quality/ 밖으로 옮기면
    # 승인 없이 고칠 수 있게 된다.
    if config.setdefault("decisions", DECISIONS_PATH) != DECISIONS_PATH:
        raise ConfigError(f"config.decisions 는 {DECISIONS_PATH} 로 고정입니다")

    tool = _require(config, "tool", dict, "config")
    for key in ("name", "version"):
        _require(tool, key, str, "config.tool")
    _check_command(_require(tool, "command", list, "config.tool"), "config.tool.command")
    timeout = tool.setdefault("timeout_seconds", 7200)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigError("config.tool.timeout_seconds 는 양수여야 합니다")
    # 버전을 확인하지 않으면 다른 버전(변이 종류가 다른) 도구로 돈 결과가 통과로 나온다
    version_command = tool.get("version_command")
    if (not isinstance(version_command, list) or not version_command
            or not all(isinstance(part, str) for part in version_command)):
        raise ConfigError("config.tool.version_command 는 문자열 목록이어야 합니다(필수)")
    status_map = tool.setdefault("status_map", {})
    if not isinstance(status_map, dict) or not all(
            isinstance(k, str) and v in STRYKER_STATUSES for k, v in status_map.items()):
        raise ConfigError("config.tool.status_map 은 {도구 상태: Stryker 상태} 객체여야 합니다")
    _string_list(tool, "suppression_markers", "config.tool", default=[])
    _string_list(tool, "config_files", "config.tool", default=[])

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
            dirs = _string_list(module, key, where)
            if not dirs:
                raise ConfigError(f"{where}.{key} 가 비어 있습니다")
            module[key] = [_norm_dir(d) for d in dirs]
        baseline = _require(module, "baseline", list, where)
        if not baseline or not all(isinstance(part, str) for part in baseline):
            raise ConfigError(f"{where}.baseline 은 문자열 목록이어야 합니다")
        if "command" in module:
            # 한 앱에 시뮬레이터 모듈과 호스트(macOS) 모듈이 섞이면 도구 인자가 다르다
            _check_command(module["command"], f"{where}.command")
        values = module.setdefault("vars", {})
        if not isinstance(values, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
            raise ConfigError(f"{where}.vars 는 {{이름: 문자열}} 객체여야 합니다")
        _string_list(module, "fingerprint", where, default=[])
    return config


def git(repo, *args):
    # 경로 이름에 *·[ 가 있어도 패턴으로 풀지 않도록 literal pathspec 으로 돌린다.
    result = subprocess.run(["git", "--literal-pathspecs", "-C", repo, *args], capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        raise IncompleteError(f"git {' '.join(args)} 실패: {stderr}")
    return result.stdout.decode("utf-8", "replace")


def _nul_paths(text):
    return [path for path in text.split("\0") if path]


_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_lines(repo, merge_base, path):
    # 한 파일의 바뀐 줄 번호. 머리줄의 경로는 읽지 않는다 — git 이 한글은 8진수로 인용하고 공백
    # 경로 끝에는 탭을 붙여, 머리줄에서 경로를 잘라 쓰면 변경이 범위에서 빠진다(실측).
    # 줄만 지운 자리(+c,0)는 새 줄이 없으므로 앞뒤 줄을 대상으로 본다.
    # --text·--no-ext-diff·--no-textconv: .gitattributes 의 -diff/binary·외부 diff 설정이 출력을
    # "Binary files differ" 로 바꿔 바뀐 줄이 사라지지 않게 한다.
    text = git(repo, "diff", "-U0", "--no-color", "--no-renames", "--text", "--no-ext-diff",
               "--no-textconv", merge_base, "--", path)
    lines = set()
    for line in text.splitlines():
        match = _HUNK.match(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2)) if match.group(2) is not None else 1
        if count == 0:
            lines.update(n for n in (start, start + 1) if n > 0)
        else:
            lines.update(range(start, start + count))
    return lines


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


def tool_config_paths(module, config):
    # 모듈별 도구 설정 파일(예: .swift-mutation-testing.yml)의 저장소 기준 경로
    return [os.path.normpath(os.path.join(module["path"], name)).replace(os.sep, "/")
            for name in config["tool"]["config_files"]]


def plan_scope(repo, config, base=None):
    # 기준 브랜치 대비 바뀐 내용으로 모듈별 검사 범위를 정한다. 작업 트리의 미커밋 변경과
    # 추적 안 된 새 파일도 포함한다 — 커밋 전 로컬 검사에서 새 파일이 빠지면 안 된다.
    base = base or config["base"]
    merge_base = git(repo, "merge-base", "HEAD", base).strip()
    # 경로 목록은 NUL 구분(-z)으로 받아 인용·이스케이프 없이 쓴다. 이름 변경은 새 파일로 본다
    # (--no-renames) — 검사 제외 위치에서 옮겨 온 로직이 "바뀐 줄 없음"으로 빠지지 않게 한다.
    changes = {}
    for path in _nul_paths(git(repo, "diff", "--name-only", "-z", "--no-renames", merge_base)):
        changes[path] = set()
    for path in _nul_paths(git(repo, "ls-files", "-z", "--others", "--exclude-standard")):
        changes[path] = None  # None = 파일 전체

    modules = {
        m["name"]: {"targets": {}, "widened": False, "source_changed": [], "test_changed": [],
                    "tool_config_changed": {}}
        for m in config["modules"]
    }
    config_owner = {path: m["name"] for m in config["modules"] for path in tool_config_paths(m, config)}
    plan = {"merge_base": merge_base, "changed": sorted(changes), "modules": modules,
            "unmapped": [], "ignored": [], "other": []}

    for path in sorted(changes):
        if path in config_owner:
            # 도구 설정은 변이 종류·제외 범위를 바꿔 검사를 조용히 줄일 수 있다. 검사 제외 패턴에
            # 걸려도 빼지 않고 바뀐 줄을 기록해 판정에서 승인을 받게 한다.
            if not os.path.exists(os.path.join(repo, path)):
                lines = "deleted"
            elif changes[path] is None:
                lines = "all"
            else:
                lines = sorted(changed_lines(repo, merge_base, path)) or [1]
            modules[config_owner[path]]["tool_config_changed"][path] = lines
            continue
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
                else:
                    lines = changed_lines(repo, merge_base, path)
                    if lines:
                        entry["targets"][path] = sorted(lines)

    for module in config["modules"]:
        entry = modules[module["name"]]
        # 테스트가 바뀌었는데 로직 코드 줄 변경이 없으면(리소스·삭제·주석만 함께 바뀐 경우 포함)
        # 테스트가 겨냥한 로직을 알 수 없으므로 모듈 로직 전체로 넓힌다.
        code_changed = any(_has_code(repo, path, lines) for path, lines in entry["targets"].items())
        if entry["test_changed"] and not code_changed:
            entry["widened"] = True
            entry["targets"] = {path: "all" for path in _module_logic_files(repo, module, config)}
    return plan


def _is_code_line(line):
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith(("//", "/*", "*"))


def _has_code(repo, path, lines):
    source = _read_lines(repo, path)
    numbers = range(1, len(source) + 1) if lines == "all" else lines
    return any(_is_code_line(source[n - 1]) for n in numbers if 0 < n <= len(source))


STRYKER_STATUSES = {
    "Killed", "Survived", "NoCoverage", "Timeout", "RuntimeError", "CompileError", "Ignored", "Pending",
}


def _components(path):
    return [part for part in path.replace("\\", "/").split("/") if part and part != "."]


def resolve_report_path(key, repo, roots, known_files):
    # 보고서의 파일 키를 저장소 기준 상대 경로로 바꾼다. 도구마다 절대 경로·프로젝트 기준·잘린
    # 경로(심볼릭 링크 경로 길이 차로 앞이 잘리는 도구 버그 실측)가 섞여 있어, 실제 파일 목록과
    # 경로 끝부분이 가장 길게 일치하는 것을 고른다. 동률이거나, 키에 폴더가 있는데 파일 이름만
    # 맞으면 판정하지 않는다(None) — 이름만 같은 다른 파일의 변이가 섞이면 결과가 거짓이 된다.
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
    if best is None or tie or best_len < min(2, len(key_parts)):
        return None
    return best


def load_report(path, repo, roots, known_files, status_map=None):
    # Stryker 보고서(mutation-testing-report-schema) → 변이 목록. 읽을 수 없거나 형식이 다르면
    # 판정 근거가 없으므로 미완료다. 도구 고유 상태는 status_map 으로 표준 상태에 대응시킨다
    # (예: swift-mutation-testing 1.5.1 은 Unviable·Crash 를 낸다).
    status_map = status_map or {}
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
            status = status_map.get(status, status) if isinstance(status, str) else status
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
    "no_mutant_expected": {"NoMutant"},
}

HINTS = {
    "Survived": "요구사항과 대조해 테스트 누락·약한 단언인지 판단하고 보강한다",
    "NoCoverage": "이 지점을 실행하는 테스트를 보강한다",
    "Timeout": "제한 시간을 늘려 다시 돌리거나, 변이가 무한 반복을 만든 근거를 판단 기록으로 남긴다",
    "RuntimeError": "다시 돌려도 같으면 근거를 판단 기록으로 남긴다",
    "Ignored": "제외 주석·설정을 걷어내거나, 승인된 판단 기록을 남긴다",
    "NoMutant": ("변이할 표기가 보이는데 도구가 이 줄에 변이를 만들지 않았다 — 도구 설정·제외 표식을 "
                 "확인하고, 변이 대상이 아닌 표기(타입 제약 등)면 승인된 판단 기록을 남긴다"),
}

AMBIGUOUS_HINT = ("같은 모양의 변이가 같은 자리에 여럿이라 판단 기록 하나로 구분할 수 없다 — "
                  "테스트로 잡거나 코드를 구분되게 고친다")

# 바뀐 줄에 이런 표기가 보이는데 그 줄 변이가 없으면, 도구가 그 줄을 분석했다는 근거가 없다고 본다.
# swift-mutation-testing v1.5.1 기본 변이 종류(관계·논리·불리언·산술·조건 부정·삼항)를 따르고
# Swift·Dart 공통 표기만 쓴다. 단독 호출 제거는 함수 본문의 유일한 문장이면 도구가 건너뛰어
# 줄만 보고는 가를 수 없으므로 넣지 않는다.
_MUTABLE_TOKEN = re.compile(
    r"==|!=|>=|<=|&&|\|\|| > | < |\btrue\b|\bfalse\b"
    r'|(?<!")\s[-+*/%]\s(?!")'  # 산술. 문자열을 잇는 + 는 도구가 변이하지 않는다
    r"|\s\?\s"  # 삼항
    r"|(?<!#)\b(?:if|guard|while)\s+(?!let\b|var\b|case\b|#)")  # 조건 부정. 값 묶기·패턴·#if 는 아니다
_STRING_LITERAL = re.compile(r'"(?:[^"\\\n]|\\.)*"')
_OPERATOR_DECL = re.compile(r"\b(?:func|operator)\s*[-=!<>+*/%&|^~?.]+")


def _mutable_token(line):
    # 줄에서 변이 대상으로 보이는 첫 표기의 (열, 표기). 없으면 None.
    # 문자열 내용·연산자 함수 이름(func ==)·주석은 변이 대상이 아니므로 같은 길이로 가린 뒤 찾는다.
    if line.lstrip().startswith(("//", "/*", "*")):
        return None
    masked = _STRING_LITERAL.sub(lambda m: '"' + "_" * (len(m.group(0)) - 2) + '"', line)
    masked = _OPERATOR_DECL.sub(lambda m: "_" * len(m.group(0)), masked)
    comment = masked.find("//")
    if comment >= 0:
        masked = masked[:comment]
    for match in _MUTABLE_TOKEN.finditer(masked):
        text = match.group(0)
        # repeat { } while 조건은 조건 목록이 아니라 도구가 부정하지 않는다
        if text.startswith("while") and masked[:match.start()].rstrip().endswith("}"):
            continue
        return match.start() + len(text) - len(text.lstrip()), text.split()[0]
    return None


def _read_lines(repo, rel):
    try:
        with open(os.path.join(repo, rel), encoding="utf-8") as handle:
            return handle.read().splitlines()
    except OSError:
        return []


def _neighbor(lines, index, step):
    i = index + step
    while 0 <= i < len(lines):
        if lines[i].strip():
            return lines[i].strip()
        i += step
    return ""


def mutant_key(repo, mutant, cache=None):
    # 판단 기록을 줄 번호가 아니라 원래 줄과 그 앞뒤 줄 내용에 묶는다. 위쪽 코드가 바뀌어 줄 번호가
    # 밀려도 기록이 따라가고, 그 자리가 바뀌면 기록이 떨어져 다시 판단하게 된다. 앞뒤 줄을 넣는 것은
    # 같은 모양의 줄(guard·return 등)을 다른 함수에 새로 써도 기존 승인이 옮겨 붙지 않게 하기 위해서다.
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
    raw = "\0".join([mutant["file"], _neighbor(lines, index, -1), stripped, _neighbor(lines, index, 1),
                     str(column), mutant["mutator"], mutant["replacement"]])
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
        # file·line_text 는 사람이 무엇을 승인하는지 보이게 하려고 필수로 둔다(해시 키만으로는 알 수 없다)
        ok = (isinstance(entry, dict)
              and isinstance(entry.get("key"), str) and entry["key"]
              and isinstance(entry.get("file"), str) and entry["file"]
              and isinstance(entry.get("line_text"), str)
              and entry.get("kind") in DECISION_KINDS
              and isinstance(entry.get("reason"), str) and entry["reason"].strip()
              and isinstance(entry.get("approved_by"), str) and entry["approved_by"].strip())
        (valid if ok else invalid).append(entry)
    return valid, invalid


def _in_scope(mutant, lines):
    if lines == "all":
        return True
    return any(mutant["start_line"] <= n <= mutant["end_line"] for n in lines)


def _lines_without_mutants(source, lines, in_scope):
    # 변이할 표기가 보이는데 변이가 없는 줄의 (줄, 열, 표기). 바뀐 줄은 줄마다 본다 — 같은 파일에
    # 변이가 하나라도 있으면 파일 단위로는 도구가 일부 줄만 건너뛴 것을 놓친다.
    # 파일 전체가 대상이면(넓힘·이동) 바뀌지 않은 줄까지 줄마다 올리지 않고, 파일에 변이가
    # 하나도 없을 때 첫 줄만 올린다.
    if lines == "all":
        if in_scope:
            return []
        numbers = range(1, len(source) + 1)
    else:
        numbers = lines
    found = []
    for number in numbers:
        if not 0 < number <= len(source):
            continue
        token = _mutable_token(source[number - 1])
        if token and not any(m["start_line"] <= number <= m["end_line"] for m in in_scope):
            found.append((number, token[0], token[1]))
            if lines == "all":
                break
    return found


def suppression_items(repo, plan, markers):
    # 도구의 변이 끄기 표식(예: @SwiftMutationTestingDisabled)은 끈 변이를 보고서에서 아예 뺀다.
    # 결과만 보면 범위가 조용히 줄어드므로, 대상 파일에서 표식을 직접 찾아 Ignored 로 올린다.
    # 표식이 바뀐 줄 밖(감싼 함수·타입)에 있어도 안쪽 변경을 끄므로 파일 전체를 본다.
    items = []
    if not markers:
        return items
    for entry in plan["modules"].values():
        for path in entry["targets"]:
            for number, line in enumerate(_read_lines(repo, path), start=1):
                # 주석을 걷어내지 않고 줄 전체에서 찾는다. 같은 줄 앞쪽 문자열에 // 가 있으면 뒤의
                # 표식을 놓친다(리뷰 재현). 주석 속 표기까지 올라오는 쪽이 판정을 막는 안전한 방향이다.
                for marker in markers:
                    column = line.find(marker)
                    if column >= 0:
                        items.append({"file": path, "start_line": number, "start_column": column + 1,
                                      "end_line": number, "mutator": "Suppression", "original": marker,
                                      "replacement": "", "status": "Ignored"})
    return items


TOOL_CONFIG_HINT = ("도구 설정이 기준 대비 바뀌었다 — 변이 종류 끄기·제외 범위 추가처럼 검사를 줄이는 "
                    "변경이면 되돌리거나, 승인된 판단 기록(ignore_approved)을 남긴다")


def tool_config_items(repo, plan):
    # 바뀐 도구 설정 줄을 Ignored 로 올린다. 줄마다 따로 올려 승인이 바뀐 줄 하나하나에 묶이게 한다.
    items = []
    for entry in plan["modules"].values():
        for path, lines in entry["tool_config_changed"].items():
            source = _read_lines(repo, path)
            if lines == "deleted":
                numbers = [1]
            elif lines == "all":
                numbers = [n for n, line in enumerate(source, start=1) if line.strip()] or [1]
            else:
                numbers = lines
            for number in numbers:
                items.append({"file": path, "start_line": number, "start_column": 1, "end_line": number,
                              "mutator": "ToolConfigChange", "original": "", "replacement": "",
                              "status": "Ignored", "hint": TOOL_CONFIG_HINT})
    return items


def judge(repo, plan, mutants, module_mutant_counts, decisions, skip_modules=(), suppressions=()):
    # 계획된 범위와 변이 결과를 test-quality.md 「상태별 판정」으로 판정한다.
    # skip_modules: 결과 자체가 없어 호출자가 이미 미완료 사유를 남긴 모듈 (사유를 겹쳐 쓰지 않는다).
    by_key = {d["key"]: d for d in decisions}
    used_keys = set()
    cache = {}
    pending = []  # 판단 기록으로만 해소되는 항목 — 모은 뒤 한꺼번에 대조한다
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
            missing = _lines_without_mutants(_read_lines(repo, path), lines, in_scope)
            for number, column, token in missing:
                item = {"file": path, "start_line": number, "start_column": column + 1, "end_line": number,
                        "mutator": "NoMutant", "original": token, "replacement": "", "status": "NoMutant"}
                key, text = mutant_key(repo, item, cache)
                pending.append(dict(item, key=key, line_text=text, hint=HINTS["NoMutant"]))
            if not in_scope:
                if not missing:
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
                    pending.append(dict(item, hint=HINTS[status]))
        if in_scope_total and in_scope_total == compile_errors:
            result["incomplete_reasons"].append(
                f"모듈 {name}: 범위 안 변이가 모두 컴파일 실패라 실제로 검사한 것이 없습니다")

    for suppression in suppressions:
        key, text = mutant_key(repo, suppression, cache)
        pending.append(dict(suppression, key=key, line_text=text, hint=suppression.get("hint", HINTS["Ignored"])))

    key_counts = {}
    for item in pending:
        key_counts[item["key"]] = key_counts.get(item["key"], 0) + 1
    for item in pending:
        decision = by_key.get(item["key"])
        if key_counts[item["key"]] > 1:
            # 같은 키가 여럿이면 기록 하나가 어느 것을 승인했는지 가를 수 없다 — 해소하지 않는다
            result["unresolved"].append(dict(item, hint=AMBIGUOUS_HINT))
        elif (decision and item["status"] in DECISION_KINDS[decision["kind"]]
              and decision["file"] == item["file"] and decision["line_text"] == item["line_text"]):
            used_keys.add(item["key"])
            result["resolved"].append(dict(item, decision=decision))
        else:
            result["unresolved"].append(item)

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
        if not (entry["targets"] or entry["source_changed"] or entry["test_changed"]
                or entry["tool_config_changed"]):
            continue
        files = set(module["fingerprint"]) | set(tool_config_paths(module, config))
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
            "modules": {name: {"targets": e["targets"], "widened": e["widened"],
                               "tool_config_changed": e["tool_config_changed"]}
                        for name, e in plan["modules"].items() if e["targets"] or e["tool_config_changed"]},
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
        if item["mutator"] == "NoMutant":
            change = f"{item['original']} 에 변이 없음"
        elif item["mutator"] == "ToolConfigChange":
            change = "도구 설정 바뀜"
        else:
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


def _module_report_files(repo, module, config):
    # 보고서 키를 맞춰 볼 후보. 검사 제외(ignore) 파일까지 넣는다 — 빼면 제외 파일의 키가 이름이
    # 비슷한 검사 대상 파일로 잘못 연결된다. 연결된 제외 파일의 변이는 범위 밖이라 판정에 들지 않는다.
    files = set()
    for rel_dir in [module["path"]] + module["sources"]:
        for dirpath, dirnames, filenames in os.walk(os.path.join(repo, rel_dir)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]  # .build 등 도구 산출물
            for filename in filenames:
                path = os.path.relpath(os.path.join(dirpath, filename), repo).replace(os.sep, "/")
                if _is_logic(path, config):
                    files.add(path)
    return sorted(files)


def judge_reports(repo, config_path, config, plan, reports, module_errors=None,
                  produced_by="judge", fingerprint_before=None):
    # reports: {모듈 이름: 결과 파일 경로}. 범위가 있는 모듈의 결과가 없으면 미완료다.
    # fingerprint_before: 도구를 돌리기 전에 잰 지문. 판정 뒤 지문과 다르면 검사 도중 내용이
    # 바뀐 것이라, 결과가 어느 내용을 검사했는지 알 수 없다.
    module_errors = module_errors or {}
    decisions, invalid = load_decisions(os.path.join(repo, config["decisions"]))
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
            loaded, unmapped = load_report(reports[name], repo, [os.path.join(repo, module["path"])],
                                           _module_report_files(repo, module, config),
                                           config["tool"]["status_map"])
        except IncompleteError as error:
            # 한 모듈의 결과가 깨져도 결과 파일은 남긴다 — CI 산출물로 사유를 볼 수 있어야 한다
            extra.append(f"모듈 {name}: {error}")
            missing.append(name)
            continue
        # 어느 파일인지 모르는 결과는 버리지 않는다 — 그 안의 생존 변이가 조용히 사라진다
        extra.extend(f"모듈 {name}: 결과의 파일 경로를 저장소 파일에 연결할 수 없습니다: {key}"
                     for key in unmapped)
        mutants.extend(loaded)
        counts[name] = len(loaded)
    judged = judge(repo, plan, mutants, counts, decisions, skip_modules=missing,
                   suppressions=suppression_items(repo, plan, config["tool"]["suppression_markers"])
                   + tool_config_items(repo, plan))
    judged["invalid_decisions"] = len(invalid)
    fingerprint_after = fingerprint(repo, config_path, config, plan)
    if fingerprint_before is not None and fingerprint_before != fingerprint_after:
        extra.append("검사 도중 코드·테스트·설정·판단 기록이 바뀌었습니다 — 다시 실행한다")
    if extra:
        judged["incomplete_reasons"] = extra + judged["incomplete_reasons"]
        judged["verdict"] = "incomplete"
    result = build_result(config, plan, judged, fingerprint_after)
    result["produced_by"] = produced_by
    return result


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
    before = fingerprint(repo, config_path, config, plan)
    tool = config["tool"]
    reports, errors = {}, {}
    version_error = None
    if tool.get("version_command") and any(e["targets"] for e in plan["modules"].values()):
        # 설정과 다른 버전의 도구는 변이 종류가 달라 검사가 조용히 약해질 수 있다(실측: 상위 버전이
        # 경계·산술 변이를 기본에서 뺐다). 버전이 맞는지 확인되지 않으면 미완료다.
        log_path = os.path.join(work_dir, "tool.version.log")
        try:
            command = [expand(part, dict(overrides, repo=repo)) for part in tool["version_command"]]
            code = _run_logged(command, repo, 60, log_path)
            with open(log_path, encoding="utf-8") as handle:
                output = handle.read().split("\n", 2)[-1]  # 명령·exit 머리줄은 빼고 본다
            exact = re.compile(r"(?<![\w.])" + re.escape(tool["version"]) + r"(?![\w.])")
            if code != 0 or not exact.search(output):
                version_error = f"도구 버전이 설정({tool['version']})과 다릅니다 — {log_path} 참고"
        except IncompleteError as error:
            version_error = f"도구 버전을 확인하지 못했습니다: {error}"
    for module in config["modules"]:
        name = module["name"]
        if not plan["modules"][name]["targets"]:
            continue
        if version_error:
            errors[name] = f"모듈 {name}: {version_error}"
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
    return judge_reports(repo, config_path, config, plan, reports, errors,
                         produced_by="run", fingerprint_before=before)


def verify(repo, config_path, config, result_path, base=None):
    # 저장된 결과가 지금 코드에 대해 유효한 통과인지 확인한다. 결과 없음·오래된 결과는 미완료.
    if not os.path.exists(result_path):
        return EXIT_INCOMPLETE, "결과 파일이 없습니다 — 검사를 실행하지 않았습니다"
    try:
        with open(result_path, encoding="utf-8") as handle:
            result = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return EXIT_INCOMPLETE, f"결과 파일을 읽을 수 없습니다 ({error})"
    if not isinstance(result, dict):
        return EXIT_INCOMPLETE, "결과 파일 형식이 맞지 않습니다"
    if result.get("produced_by") != "run":
        # judge 는 이미 있는 보고서를 판정할 뿐 기준 테스트·도구 실행을 거치지 않는다
        return EXIT_INCOMPLETE, "run 으로 만든 결과가 아닙니다 — 변이 도구를 실제로 돌린 결과만 인정한다"
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
