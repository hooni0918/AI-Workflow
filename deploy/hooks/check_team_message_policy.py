#!/usr/bin/env python3
"""팀 에이전트 shutdown 요청 차단."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import deny, read_payload  # noqa: E402

payload = read_payload()
tool_input = payload.get("tool_input")
message = tool_input.get("message") if isinstance(tool_input, dict) else None

if isinstance(message, dict) and message is not None and message.get("type") == "shutdown_request":
    deny(
        "팀 에이전트 shutdown 금지. 사용자가 /exit으로 직접 세션을 종료하므로 AI가 shutdown을 보낼 필요가 없습니다."
    )
