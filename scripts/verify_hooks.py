#!/usr/bin/env python3
import sys

from hook_guard import ensure_hooks_ready

try:
    ensure_hooks_ready()
    print("AC git hook 준비 상태 정상")
except Exception as error:
    sys.stderr.write(f"{error}\n")
    sys.exit(1)
