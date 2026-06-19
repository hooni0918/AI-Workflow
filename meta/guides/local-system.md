# Local System Sync

전역 `sync-system`의 로컬판. 한 명령으로 repo-local 산출물 전부를 배포합니다 — **로컬 스킬**(cross-repo)과 **settings/hooks**(이 레포 전용).

```bash
make sync-local-system
```

> sync 명령은 사용자만 실행합니다. 에이전트는 `block-ac-sync` 훅에 막히므로, 사용자가 직접 `make sync-local-system`으로 실행하세요.

## 수행 작업

시작 시 git hook 준비 상태와 로컬 settings 생성 계약(`make verify-local-system`)을 먼저 확인합니다(fail-fast).

### 1. 로컬 자산 (cross-repo)

- `local/` 하위 디렉토리(`skills` 등, `hooks` 제외)를 `.claude/<X>`와 `.agents/<X>` **양쪽**으로 복사합니다. claude·codex가 같은 자산을 쓰므로 동일 복사이며, hooks만 2)에서 타겟별로 따로 투영합니다.
- 레포 루트 `CLAUDE.md`가 있으면 `AGENTS.md` 및 `GEMINI.md`로 복사합니다.
- 원본은 `local/`이며, `.claude/<X>`·`.agents/<X>`는 배포 산출물로 봅니다(gitignore).

### 2. settings/hooks (이 레포 전용)

전역 `sync-system`과 **동일한 메커니즘**(base+override 부분키 머지·생성 계약 fail-fast·배포 후 대조)을 repo-local에 적용합니다. 소스는 `local/`(전역 `deploy/`의 로컬판).

- `local/base-settings.json`(논리 hook) + `local/claude-settings.json`(override) → `.claude/settings.json`에 **부분 머지**(사용자 키 보존).
- 같은 논리 hook → `.codex/hooks.json`에 **whole-file** 기록(codex 정책).
- `local/hooks/*.py` → `.claude/hooks/`·`.codex/hooks/`로 복사.
- codex 프로젝트-로컬 훅은 trusted여야 발화합니다. 배포 시 best-effort로 trust를 시도하고, 실패하면 codex 세션에서 `/hooks`로 `.codex/hooks.json`을 수동 신뢰하세요.

산출물(`.claude/settings.json`·`.claude/hooks/`·`.codex/`)은 **gitignore**되며 트래킹하지 않습니다. 소스(`local/`)만 커밋합니다.

## 제거

```bash
make unsync-local-system
```

- **로컬 자산**: `.claude/<X>`·`.agents/<X>`·`AGENTS.md`·`GEMINI.md`는 원본(`local/<X>`·`CLAUDE.md`)과 동일할 때만 삭제합니다. 다르면 사용자 수정 가능성이 있으므로 `skipped`로 보고합니다.
- **settings/hooks**: `.claude/settings.json`은 이 레포가 넣은 top-level 키만 부분 제거(사용자 키 보존), `.codex/hooks.json`·`.codex/hooks`·`.claude/hooks`는 전유라 통째 제거합니다.

## 반복 실행 기준

여러 번 실행해도 현재 소스 내용을 기준으로 같은 상태로 수렴해야 합니다. 로컬 자산은 `local/<X>`·`CLAUDE.md` 기준으로, settings/hooks는 `local/` 기준으로 재생성(기존 산출물 먼저 제거 → 고아 방지)합니다.

## 생성 계약 검증

```bash
make verify-local-system
```

`local/base-settings.json`에서 만든 hooks가 claude·codex 양쪽에 등록되는지, command가 repo-relative(`python3 .claude/hooks/`·`python3 .codex/hooks/`)인지, codex 매처가 올바른지 검증합니다. `sync-local-system` 시작 시 fail-fast로 호출됩니다.
