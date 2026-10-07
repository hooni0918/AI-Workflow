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
import json
import os
import re
import sys

RUNNER_VERSION = "0.1.0"

EXIT_PASS = 0
EXIT_UNRESOLVED = 1
EXIT_INCOMPLETE = 2
EXIT_USAGE = 3


class ConfigError(Exception):
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="변이 검사 게이트")
    parser.add_argument("--version", action="version", version=RUNNER_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-config", help="설정 파일만 검증한다")
    check.add_argument("--config", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "check-config":
            load_config(args.config)
            print("설정 정상")
            return EXIT_PASS
    except ConfigError as error:
        print(f"설정 오류: {error}", file=sys.stderr)
        return EXIT_USAGE
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
