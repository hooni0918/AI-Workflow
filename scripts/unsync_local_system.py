#!/usr/bin/env python3
# AC 로컬 배포 제거(전역 unsync:system의 로컬판). sync:local-system이 만든 산출물을 되돌린다:
#   1) 로컬 자산: .claude/<X>·.agents/<X>·AGENTS.md·GEMINI.md (원본과 동일할 때만 제거)
#   2) AC settings/hooks: .claude/settings.json은 AC 키만 부분 제거(사용자 키 보존),
#      .codex/hooks.json·.codex/hooks·.claude/hooks는 AC 전유라 통째 제거, .ac-keys 정리
from unsync_local_skills import unsync_local_skills
from local_deploy_lib import uninstall_local


def main():
    # 1) 로컬 스킬 (cross-repo).
    unsync_local_skills()

    # 2) AC settings/hooks.
    print("")
    print("AC 로컬 settings/hooks 제거 중...")
    print("---")
    removed = uninstall_local(print)
    print(f"\n제거 완료: {removed}건")


if __name__ == "__main__":
    main()
