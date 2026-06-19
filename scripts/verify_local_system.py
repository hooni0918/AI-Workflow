#!/usr/bin/env python3
# 로컬 settings/hooks 생성 계약 검증 (전역 verify_settings_projection.py의 로컬판).
# sync:local-system 시작 시 fail-fast로 호출된다.
import re
import sys

from settings_projection import build_hooks, LOCAL_ADAPTERS, local_hook_command
from local_deploy_lib import load_local_base_settings

build_opts = {"adapters": LOCAL_ADAPTERS, "makeCommand": local_hook_command}


# build_hooks 출력 → [{event, matcher, file}] 평탄화. command가 `python3 <dir>/hooks/<file>`
# 형식이라 file과 dir 토큰을 거기서 추출한다.
def flatten(hooks_obj):
    out = []
    for event in hooks_obj:
        for group in hooks_obj[event]:
            for h in group["hooks"]:
                m = re.search(r"/hooks/([^\s\"/]+)", h["command"])
                out.append(
                    {
                        "event": event,
                        "matcher": group["matcher"] if "matcher" in group else None,
                        "file": m.group(1) if m else None,
                        "command": h["command"],
                    }
                )
    return out


def main():
    base = load_local_base_settings()
    failures = []

    def check(cond, msg):
        if cond:
            print(f"  PASS  {msg}")
        else:
            sys.stderr.write(f"  FAIL  {msg}\n")
            failures.append(msg)

    print("로컬 settings 생성 계약 검증 중...")

    check(isinstance(base.get("hooks"), list), "local base.hooks는 논리 hook 배열")

    claude = flatten(build_hooks(base["hooks"], "claude", build_opts))
    codex = flatten(build_hooks(base["hooks"], "codex", build_opts))
    base_files = [_py_name(h["file"]) for h in base["hooks"]]

    # claude: 모든 논리 hook 등록, command가 repo-relative .claude/hooks, PreToolUse 매처 Bash
    check(
        all(any(h["file"] == f for h in claude) for f in base_files),
        "claude: base의 모든 hook 등록됨",
    )
    check(
        all(
            ".claude/hooks/" in h["command"] and h["command"].startswith("python3 ")
            for h in claude
        ),
        "claude: command가 repo-relative python3 .claude/hooks/",
    )
    claude_pre = [h for h in claude if h["event"] == "PreToolUse"]
    check(
        len(claude_pre) > 0 and all(h["matcher"] == "Bash" for h in claude_pre),
        "claude: PreToolUse 매처 Bash",
    )

    # codex: 모든 논리 hook 등록, command가 .codex/hooks, PreToolUse가 run_command+Bash, UserPromptSubmit 없음
    check(
        all(any(h["file"] == f for h in codex) for f in base_files),
        "codex: base의 모든 hook 등록됨",
    )
    check(
        all(
            ".codex/hooks/" in h["command"] and h["command"].startswith("python3 ")
            for h in codex
        ),
        "codex: command가 repo-relative python3 .codex/hooks/",
    )
    codex_pre = [h for h in codex if h["event"] == "PreToolUse"]
    check(
        any(h["matcher"] == "run_command" for h in codex_pre)
        and any(h["matcher"] == "Bash" for h in codex_pre),
        "codex: PreToolUse가 run_command+Bash로 분리됨",
    )
    check(not any(h["event"] == "UserPromptSubmit" for h in codex), "codex: UserPromptSubmit 없음")

    if len(failures) > 0:
        sys.stderr.write(f"\n로컬 settings 생성 계약 실패: {len(failures)}건\n")
        sys.exit(1)
    print("로컬 settings 생성 계약 정상")


def _py_name(name):
    return name


if __name__ == "__main__":
    main()
