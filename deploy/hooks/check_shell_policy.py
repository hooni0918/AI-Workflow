#!/usr/bin/env python3
"""shell 정책: git reset --hard/--mixed, cd && git 차단."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import deny, get_command, read_payload  # noqa: E402

cmd = get_command(read_payload())

if re.search(r"\bgit\b.*--(hard|mixed)\b", cmd):
    deny(
        "git reset --hard / --mixed 금지. --soft만 사용하세요. 워킹 디렉터리 미커밋 변경이 복구 불가능하게 삭제됩니다."
    )

# cd <dir> && git: 대상 폴더의 .git/hooks 실행 위험 → Claude Code가 무조건 권한 프롬프트(allowlist·hook allow로 우회 불가).
# git -C <path>로 강제 교정.
has_cd_sub = re.search(r"(?:^|&&|\|\||;|\|)\s*cd\s", cmd) is not None
has_git_sub = re.search(r"(?:^|&&|\|\||;|\|)\s*git\s", cmd) is not None
if has_cd_sub and has_git_sub:
    deny(
        "cd && git 금지 — 다른 디렉터리의 git은 'git -C <path> <cmd>' 형태로 실행하세요. cd로 이동 후 git을 돌리면 대상 폴더의 .git/hooks가 실행될 수 있어 Claude Code가 무조건 권한 프롬프트를 띄웁니다(allowlist·hook allow로 우회 불가)."
    )
