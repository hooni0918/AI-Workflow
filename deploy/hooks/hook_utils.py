"""Claude Code hook 공통 유틸.

Claude Code hook 계약:
- stdin으로 JSON 이벤트를 받는다.
- 판정은 stdout으로 JSON을 쓰고 종료코드 0으로 끝낸다.
  (deny/addContext 후 종료코드 0으로 통과)
"""
import json
import sys


def read_payload():
    return json.loads(sys.stdin.buffer.read().decode("utf-8"))


def get_command(payload):
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
        return tool_input["command"]
    return ""


def get_cwd(payload):
    cwd = payload.get("cwd")
    return cwd if isinstance(cwd, str) else ""


def get_session_id(payload):
    session_id = payload.get("session_id")
    return session_id if isinstance(session_id, str) else ""


def deny(reason):
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def add_context(context, hook_event_name="UserPromptSubmit"):
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                    "additionalContext": context,
                }
            }
        )
    )
    sys.exit(0)
