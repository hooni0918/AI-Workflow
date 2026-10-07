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
import json
import os
import re
import subprocess
import sys

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
    command = _require(tool, "command", list, "config.tool")
    if not command or not all(isinstance(part, str) for part in command):
        raise ConfigError("config.tool.command 는 문자열 목록이어야 합니다")
    if "{report}" not in " ".join(command):
        raise ConfigError("config.tool.command 에 {report} 자리표시자가 있어야 합니다")
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
    except ConfigError as error:
        print(f"설정 오류: {error}", file=sys.stderr)
        return EXIT_USAGE
    except IncompleteError as error:
        print(f"검사 미완료: {error}", file=sys.stderr)
        return EXIT_INCOMPLETE
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
