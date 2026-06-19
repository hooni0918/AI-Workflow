# Sync Guides

> 이 가이드는 AI 에이전트가 읽고 따라 실행하는 것을 전제로 작성되었습니다.

배포·hook 인프라는 Python으로 포팅되어 있습니다. 모든 명령은 `Makefile` 타겟이며 내부적으로 `python3 scripts/*.py`를 호출합니다.

- [환경 동기화](environment.md): 현재 사용자 환경을 이 레포 기준으로 맞춥니다.
- [시스템 자산 동기화](system.md): Claude/Codex/Gemini 등 에이전트 시스템 자산을 이 레포 기준으로 맞춥니다.
- [로컬 시스템 동기화](local-system.md): 로컬 스킬(cross-repo)과 settings/hooks를 한 명령으로 맞춥니다.

## 명령 이름 기준

- `make sync-*`: 이 레포가 관리하는 원하는 상태로 맞춥니다. 반복 실행해도 같은 상태로 수렴해야 합니다.
- `make unsync-*`: 대응하는 `sync-*`가 만든 관리 산출물만 제거합니다.
- `make verify-hooks`: 워크트리의 git `commit-msg` hook(`scripts/commit_msg.py` 연결) 준비 상태를 확인합니다. 새 worktree에서 커밋하기 전에 실행합니다.
- `make verify-settings`: `deploy/base-settings.json`에서 타겟별 설정을 생성하는 계약을 확인합니다. `sync-system`이 시작 시 자동 실행합니다.
- `make verify-local-system`: `local/base-settings.json`에서 repo-local 설정을 생성하는 계약을 확인합니다. `sync-local-system`이 시작 시 자동 실행합니다.

## 새 대상 추가 기준

새 설치·동기화 대상을 추가할 때는 같은 변경 안에서 다음 항목을 함께 맞춥니다.

- `Makefile`에 `sync-<target>`과 `unsync-<target>` 타겟을 함께 등록합니다.
- `scripts/sync_<target>.py`와 `scripts/unsync_<target>.py`를 함께 추가합니다.
- `meta/guides/<target>.md`에 수행 작업, 제거 기준, 반복 실행 기준을 적습니다.
- 이 인덱스와 `meta/INSTALLATION_GUIDE.md`에 새 대상이 필요한 사용자 흐름을 반영합니다.
- `sync-<target>`은 2회 이상 실행해도 중복 산출물을 만들지 않아야 합니다.
- `unsync-<target>`은 marker block, 상태 파일, 동일성 비교 중 하나로 이 레포가 만든 산출물만 제거해야 합니다.
