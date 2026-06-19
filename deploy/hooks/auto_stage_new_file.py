#!/usr/bin/env python3
"""아직 git에 없는 새 파일을 PostToolUse에서 자동 stage."""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import read_payload  # noqa: E402

payload = read_payload()
tool_input = payload.get("tool_input")
file_path = ""
if isinstance(tool_input, dict) and isinstance(tool_input.get("file_path"), str):
    file_path = tool_input["file_path"]

if not file_path or re.search(r"[/\\](evals|workspace)[/\\]", file_path):
    sys.exit(0)

try:
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", file_path],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
except Exception:
    try:
        subprocess.run(
            ["git", "add", file_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": f"새 파일 자동 staged: {file_path}",
                    }
                }
            )
        )
    except Exception:
        pass
