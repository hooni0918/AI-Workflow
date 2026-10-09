# Python 포팅된 배포/hook 인프라 진입점.
# 원본 package.json scripts(node scripts/*.js)에 1:1 대응하는 타겟(python3 scripts/*.py).
#
# 사용 예:
#   make sync-system        # 전역 배포 (~/.claude, ~/.codex, ~/.gemini)
#   make unsync-system
#   make sync-local-system  # repo-local .claude/.codex 배포
#   make install-hooks      # .git/hooks/commit-msg 에 commit_msg.py 연결

PYTHON ?= python3
SCRIPTS := scripts
GIT_HOOKS_DIR := $(shell git rev-parse --git-path hooks 2>/dev/null)

.PHONY: sync-system unsync-system \
        sync-local-system unsync-local-system \
        sync-local-skills unsync-local-skills \
        verify-hooks verify-settings verify-local-system verify-test-quality verify-test-quality-e2e \
        install-hooks uninstall-hooks

# --- system (package.json: sync:system / unsync:system) ---
sync-system:
	$(PYTHON) $(SCRIPTS)/sync_system.py

unsync-system:
	$(PYTHON) $(SCRIPTS)/unsync_system.py

# --- local-system (package.json: sync:local-system / unsync:local-system) ---
sync-local-system:
	$(PYTHON) $(SCRIPTS)/sync_local_system.py

unsync-local-system:
	$(PYTHON) $(SCRIPTS)/unsync_local_system.py

# --- local-skills (sync_local_system이 내부에서 호출하지만 단독 실행도 가능) ---
sync-local-skills:
	$(PYTHON) $(SCRIPTS)/sync_local_skills.py

unsync-local-skills:
	$(PYTHON) $(SCRIPTS)/unsync_local_skills.py

# --- verify (package.json: verify:hooks / verify:settings / verify:local-system) ---
verify-hooks:
	$(PYTHON) $(SCRIPTS)/verify_hooks.py

verify-settings:
	$(PYTHON) $(SCRIPTS)/verify_settings_projection.py

verify-local-system:
	$(PYTHON) $(SCRIPTS)/verify_local_system.py

# test-quality 스킬의 변이 검사 게이트 회귀 검증
verify-test-quality:
	$(PYTHON) $(SCRIPTS)/verify_test_quality.py

# 결제 예제에 실제 변이 도구를 돌리는 실측. 도구가 없으면 확인 불가(exit 2). SMT=<도구 경로>로 지정 가능
verify-test-quality-e2e:
	$(PYTHON) $(SCRIPTS)/e2e_test_quality.py

# --- git commit-msg hook 연결 (원본 husky prepare 대체) ---
# .git/hooks/commit-msg 에 scripts/commit_msg.py 를 호출하는 shim을 설치한다.
install-hooks:
	@if [ -z "$(GIT_HOOKS_DIR)" ]; then echo "git 레포가 아닙니다 — commit-msg 훅 설치를 건너뜁니다"; exit 0; fi
	@mkdir -p "$(GIT_HOOKS_DIR)"
	@printf '#!/bin/sh\nexec %s "$$(git rev-parse --show-toplevel)/scripts/commit_msg.py" "$$1"\n' '$(PYTHON)' > "$(GIT_HOOKS_DIR)/commit-msg"
	@chmod +x "$(GIT_HOOKS_DIR)/commit-msg"
	@chmod +x "$(SCRIPTS)/commit_msg.py"
	@echo "installed commit-msg hook -> $(GIT_HOOKS_DIR)/commit-msg"

uninstall-hooks:
	@rm -f "$(GIT_HOOKS_DIR)/commit-msg"
	@echo "removed commit-msg hook from $(GIT_HOOKS_DIR)/commit-msg"
