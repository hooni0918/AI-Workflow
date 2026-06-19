#!/usr/bin/env python3
"""로컬 정책 훅: 에이전트가 sync 스크립트를 직접 실행하지 못하게 막는다.

에이전트(Claude·Codex)가 `make sync-*` / `python3 scripts/sync_*.py`를 직접 실행하지
못하게 막는다. sync는 사용자만 실행한다 (`! make sync-system` 등).

이 파일은 `local/hooks/`의 원본이며, `make sync-local-system`이 repo-local
`.claude/hooks/`·`.codex/hooks/`로 배포한다. 직접 산출물을 수정하지 말 것.
"""
import json
import re
import sys


def read_input():
    try:
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        return None


def get_command(payload):
    """Claude(tool_input.command) / Codex(toolCall.args.CommandLine 등) 페이로드 모양을 모두 커버."""
    if not payload:
        return ""

    def _get(d, *keys):
        cur = d
        for k in keys:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    return (
        _get(payload, "tool_input", "command")
        or _get(payload, "tool_input", "args", "command")
        or _get(payload, "toolCall", "args", "CommandLine")
        or _get(payload, "toolCall", "args", "command")
        or ""
    )


cmd = get_command(read_input())

# 명령 경계(시작·연결자)에 앵커한다. echo·grep 등에 문자열로 들어가도
# 그건 차단하지 않고, 실제로 명령으로 실행되는 경우만 막는다.
if isinstance(cmd, str) and re.search(
    r"(?:^|&&|\|\||[;|]|\$\(|`)\s*(?:make\s+(?:un)?sync-|python3?\s+scripts/(?:un)?sync_)", cmd
):
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "sync is reserved for the user only. The agent must not call sync scripts. "
                        "The user runs them with `! make sync-system` (or `python3 scripts/sync_*.py`)."
                    ),
                }
            }
        )
    )

sys.exit(0)
