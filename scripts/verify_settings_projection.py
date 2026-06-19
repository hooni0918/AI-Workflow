#!/usr/bin/env python3
# settings_projection.py의 생성 계약을 회귀 검증한다.
#
# base-settings.json의 타겟별 소스를 단일화하면서, 타겟 간 hook 구조 차이(런타임 제약)는
# 어댑터가 보존해야 한다. 어댑터를 잘못 건드리면 배포본이 조용히 달라지므로, 생성 결과의
# 핵심 불변식을 기계로 확인한다. sync:system 시작 시 fail-fast로 돌아 깨진 채 배포되는 것을 막는다.

import json
import os
import re
import sys

from settings_projection import build_hooks, hook_py_name

base_settings_source = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "deploy", "base-settings.json"
)


def flatten(hooks_obj):
    # event별 그룹 → [{event, matcher, file}] 평탄화 (file은 command에서 추출)
    # command가 python3 "<...>/hooks/<file>.py" 형식이라 그 .py 파일명을 추출한다.
    out = []
    for event in hooks_obj:
        for group in hooks_obj[event]:
            for h in group["hooks"]:
                m = re.search(r"[\\/]hooks[\\/]([^\\/\s\"']+)", h["command"])
                out.append(
                    {
                        "event": event,
                        "matcher": group["matcher"] if "matcher" in group else None,
                        "file": m.group(1) if m else None,
                    }
                )
    return out


def main():
    if not os.path.exists(base_settings_source):
        sys.stderr.write(f"base-settings.json 없음: {base_settings_source}\n")
        sys.exit(1)
    with open(base_settings_source, "r", encoding="utf-8") as handle:
        base = json.loads(handle.read())
    failures = []

    def check(cond, msg):
        if cond:
            print(f"  PASS  {msg}")
        else:
            sys.stderr.write(f"  FAIL  {msg}\n")
            failures.append(msg)

    print("settings 생성 계약 검증 중...")

    check(isinstance(base.get("hooks"), list), "base.hooks는 논리 hook 배열")

    claude = flatten(build_hooks(base["hooks"], "claude"))
    codex = flatten(build_hooks(base["hooks"], "codex"))
    # base file 이름을 그대로 비교한다.
    base_files = [hook_py_name(h["file"]) for h in base["hooks"]]

    # claude: 모든 논리 hook 등록, command 토큰 .claude
    check(
        all(any(h["file"] == f for h in claude) for f in base_files),
        "claude: base의 모든 hook 등록됨",
    )
    claude_hooks = build_hooks(base["hooks"], "claude")
    claude_hooks_json = json.dumps(claude_hooks)
    check(
        claude_hooks.get("PostToolUse") is not None
        and (
            os.path.join(".claude", "hooks") in claude_hooks_json
            or ".claude/hooks" in claude_hooks_json
        ),
        "claude: command dir 토큰 .claude",
    )

    # claude: UserPromptSubmit 존재(매처 없는 그룹), PreToolUse는 Bash/SendMessage 분리
    check(
        any(h["event"] == "UserPromptSubmit" and h["matcher"] is None for h in claude),
        "claude: UserPromptSubmit(매처 없음) 존재",
    )
    claude_pre = [h for h in claude if h["event"] == "PreToolUse"]
    check(
        any(h["matcher"] == "Bash" for h in claude_pre)
        and any(h["matcher"] == "SendMessage" for h in claude_pre),
        "claude: PreToolUse가 Bash/SendMessage로 분리됨",
    )

    # search(on) 항목은 배열 매처 fan-out으로 Glob·Grep 양쪽에 등록된다
    check(
        any(h["matcher"] == "Glob" and h["file"] == "surface_claude_md.py" for h in claude_pre)
        and any(h["matcher"] == "Grep" and h["file"] == "surface_claude_md.py" for h in claude_pre),
        "claude: surface-claude-md가 Glob·Grep 매처로 fan-out 등록됨",
    )

    # codex: UserPromptSubmit 없음, PreToolUse 전부 단일 '*'
    check(not any(h["event"] == "UserPromptSubmit" for h in codex), "codex: UserPromptSubmit 없음")
    codex_pre = [h for h in codex if h["event"] == "PreToolUse"]
    check(
        len(codex_pre) > 0 and all(h["matcher"] == "*" for h in codex_pre),
        "codex: PreToolUse 전부 단일 * 매처",
    )
    codex_hooks = build_hooks(base["hooks"], "codex")
    codex_hooks_json = json.dumps(codex_hooks)
    check(
        os.path.join(".codex", "hooks") in codex_hooks_json or ".codex/hooks" in codex_hooks_json,
        "codex: command dir 토큰 .codex",
    )
    # codex는 UserPromptSubmit 이벤트 hook(surface-backlog)과 EnterWorktree 전용 hook
    # (codex엔 그 tool이 없음)만 빠지고 나머지는 전부 등록
    codex_excluded = [
        hook_py_name(h["file"])
        for h in base["hooks"]
        if h["event"] == "UserPromptSubmit" or h["on"] == "enterworktree"
    ]
    check(
        all(
            any(h["file"] == f for h in codex)
            for f in base_files
            if f not in codex_excluded
        ),
        "codex: UserPromptSubmit·EnterWorktree 외 모든 hook 등록됨",
    )
    check(
        not any(h["file"] == "post_enterworktree_install.py" for h in codex),
        "codex: EnterWorktree 전용 hook 미등록",
    )

    if failures:
        sys.stderr.write(f"settings 생성 계약 검증 실패: {len(failures)}건\n")
        sys.exit(1)
    print("settings 생성 계약 정상")


if __name__ == "__main__":
    main()
