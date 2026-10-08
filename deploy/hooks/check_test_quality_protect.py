#!/usr/bin/env python3
"""변이 검사 판정 파일 보호 훅.

test_quality_protected.txt에 적힌 파일(판단 기록·검사 설정·결과·도구 설정)을 AI가 고치려 하면
사용자 허락을 받는다. 판단 기록은 "사람이 승인한 기록만 해소"가 기준이라, AI가 승인자까지
채우면 자기 승인이 된다. 프롬프트 문구만으로는 이를 보장할 수 없어 훅으로 강제한다.

- Claude: permissionDecision "ask" — 실행 직전에 허락 창을 띄운다. auto 모드에서도 뜬다.
- Codex: "ask"를 지원하지 않아 deny로 막고 사용자가 직접 고치게 한다.

게이트(mutation_gate.py)는 설정·결과 경로를 인자로 받는다. 다른 명령과 이어 붙이지 않은
단독 실행이면 묻지 않는다 — 이어 붙인 명령은 보호 파일을 함께 고칠 수 있어 묻는다.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import deny, read_payload  # noqa: E402

PROTECTED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_quality_protected.txt")

_READ_ONLY_TOOLS = ("Read", "Glob", "Grep")
_FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
_CHAINING = re.compile(r"[;&|<>`\n]|\$\(")


def is_codex():
    return "/.codex/" in os.path.abspath(__file__).replace("\\", "/")


def load_patterns():
    try:
        with open(PROTECTED_FILE, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def ask(reason):
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )
    sys.exit(0)


def touched_text(payload):
    # 보호 대상 여부를 볼 문자열. None이면 보지 않는다(읽기 전용 도구, 게이트 단독 실행).
    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict) or tool in _READ_ONLY_TOOLS:
        return None
    if tool in _FILE_TOOLS:
        return str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    command = tool_input.get("command")
    if isinstance(command, str) and "mutation_gate.py" in command and not _CHAINING.search(command):
        return None
    return json.dumps(tool_input, ensure_ascii=False)


def main():
    payload = read_payload()
    patterns = load_patterns()
    text = touched_text(payload)
    if not patterns or text is None:
        return
    hits = [pattern for pattern in patterns if pattern in text]
    if not hits:
        return
    reason = (
        f"변이 검사 판정을 바꾸는 파일입니다({', '.join(hits)}). 판단 기록 승인·검사 범위 변경·결과는 "
        "사람이 확인합니다 — 근거와 승인자, 범위가 줄지 않았는지 보고 허락하세요."
    )
    if is_codex():
        deny(reason + " Codex는 허락 창을 띄울 수 없어 막습니다. 사용자가 직접 고치세요.")
    ask(reason)


if __name__ == "__main__":
    main()
