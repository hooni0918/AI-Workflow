#!/usr/bin/env python3
"""git add . / -A 차단, git commit -a 계열 차단."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import deny, get_command, read_payload  # noqa: E402

cmd = get_command(read_payload())

# cmd 전체를 regex로 보면 commit 메시지 안의 옵션 단어가 false positive를 만든다.
# 명령 chain을 분리해 segment 단위로, commit 옵션은 메시지 인수(-m / --message) 이전까지만 검사한다.
for segment in re.split(r"(?:&&|\|\||;)", cmd):
    trimmed = segment.strip()

    if re.search(r"^git\s+add\s+(-A|\.)(?=\s|$)", trimmed):
        deny("git add . / git add -A 금지. 파일을 개별 지정하세요.")

    # commit -a 단독, short option bundle(-am, -vam 등 a 포함), --all을 모두 차단.
    # --amend / --allow-empty는 단어 경계 매치 실패로 false positive 발생 안 함.
    commit_match = re.match(r"^git\s+commit\b(.*)", trimmed, re.DOTALL)
    if commit_match:
        before_message = re.split(r"\s(?:-m|--message)\b", commit_match.group(1))[0]
        if re.search(r"\s-[a-zA-Z]*a[a-zA-Z]*(?=\s|$)", before_message) or re.search(
            r"\s--all\b", before_message
        ):
            deny("git commit -a (auto-stage 옵션) 금지. 파일을 개별 지정하세요.")
