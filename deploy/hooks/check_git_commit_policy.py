#!/usr/bin/env python3
"""bare git commit / --no-verify / U+FFFD 차단."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import deny, get_command, read_payload  # noqa: E402

cmd = get_command(read_payload())

if re.search(r"\bgit\s+commit\s+(-\S+\s+)*(-m|--message)\b", cmd):
    deny(
        "bare git commit 금지. staging area race condition 방지를 위해 파일을 직접 지정하세요: git commit <files> -m msg"
    )

if re.search(r"\bgit\s+commit\b.*--no-verify\b", cmd):
    deny("--no-verify 금지. pre-commit hook을 우회하지 마세요.")

if re.search(r"\bgit\s+commit\b", cmd) and "�" in cmd:
    deny("커밋 메시지에 깨진 문자(U+FFFD)가 포함되어 있습니다. 메시지를 다시 작성하세요.")
