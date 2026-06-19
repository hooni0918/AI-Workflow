#!/usr/bin/env python3
# AC 로컬 배포(전역 sync:system의 로컬판). 한 명령으로 로컬 산출물 전부를 배포한다:
#   1) 로컬 자산(스킬 등): 각 레포 local/<X> → .claude/<X>·.agents/<X> (claude·codex 공통),
#      CLAUDE.md → AGENTS.md·GEMINI.md. hooks는 2)가 따로 투영하므로 제외.
#   2) AC settings/hooks: local/ 소스 → repo-local .claude/settings.json·.codex/hooks.json
#
# settings/hooks는 전역 sync:system과 동일한 메커니즘(부분키 머지·생성 계약 fail-fast·배포
# 후 대조)을 repo-local·AC 전용으로 적용한다. 산출물은 gitignore되며, 사용자만
# `make sync-local-system`으로 실행한다(에이전트는 block_ac_sync 훅에 막힘).
import os
import subprocess
import sys

from hook_guard import ensure_hooks_ready
from deploy_lib import ensure_dir, trust_codex_hooks, verify_json_exact, verify_settings, repo_dir
from sync_local_skills import sync_local_skills
from local_deploy_lib import (
    copy_local_hooks,
    local_claude_settings_object,
    local_claude_settings_path,
    local_codex_dir,
    local_codex_hooks_object,
    local_codex_hooks_path,
    merge_settings,
    uninstall_local,
    write_json,
)

_script_dir = os.path.dirname(os.path.abspath(__file__))


def main():
    ensure_hooks_ready()

    # 생성 계약이 깨지면 배포 전에 중단(fail-fast).
    subprocess.run(
        [sys.executable, os.path.join(_script_dir, "verify_local_system.py")],
        check=True,
    )

    # 1) 로컬 스킬 (cross-repo). hooksReady는 위에서 이미 확인했으므로 생략.
    print("")
    sync_local_skills({"ensureHooks": False})

    # 2) AC settings/hooks (AC 전용).
    print("")
    print("AC 로컬 settings/hooks 배포 중...")
    print("---")

    # 기존 AC 산출물 제거 후 재생성(고아 방지).
    uninstall_local(print)

    copy_local_hooks(print)

    merge_settings(local_claude_settings_object(), local_claude_settings_path)
    print("  MERGE .claude/settings.json")

    ensure_dir(local_codex_dir)
    write_json(local_codex_hooks_path, local_codex_hooks_object())
    print("  WRITE .codex/hooks.json")

    # 배포 후 검증: claude는 부분키 머지 결과, codex는 whole-file 일치.
    print("")
    print("검증 중...")
    failures = []
    if verify_settings(local_claude_settings_object(), local_claude_settings_path):
        print("  PASS  .claude/settings.json (merged)")
    else:
        failures.append(".claude/settings.json 머지 결과 키 불일치")
        sys.stderr.write("  FAIL  .claude/settings.json 머지 결과 키 불일치\n")
    if verify_json_exact(local_codex_hooks_object(), local_codex_hooks_path):
        print("  PASS  .codex/hooks.json")
    else:
        failures.append(".codex/hooks.json 내용 불일치")
        sys.stderr.write("  FAIL  .codex/hooks.json 내용 불일치\n")

    # codex 프로젝트-로컬 훅은 trusted여야 발화한다. best-effort로 trust를 시도하고,
    # 실패하면 사용자에게 `/hooks` 수동 신뢰를 안내한다(환경에 따라 app-server 불가).
    try:
        trusted = trust_codex_hooks(local_codex_dir, print, repo_dir)
        if trusted == 0:
            sys.stderr.write(
                "  WARN  codex hook trust 항목 없음 — codex 세션에서 `/hooks`로 신뢰가 필요할 수 있습니다.\n"
            )
    except Exception as error:
        sys.stderr.write(f"  WARN  codex hook trust 건너뜀: {error}\n")
        sys.stderr.write("  WARN  codex 세션에서 `/hooks`로 .codex/hooks.json을 수동 신뢰하세요.\n")

    if len(failures) > 0:
        sys.stderr.write(f"\n배포 검증 실패: {len(failures)}건\n")
        sys.exit(1)
    print("\nAC 로컬 배포 완료 (스킬 + settings/hooks)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        sys.stderr.write(f"{error}\n")
        sys.exit(1)
