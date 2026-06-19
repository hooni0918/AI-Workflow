## 스킬·프롬프트 수정 시 사전 참조

`deploy/` 또는 `local/` 하위를 수정할 때, 작업 시작 전에 `/scw` 스킬 본체와 그 특화 체크리스트(`local/skills/scw/specialized/`)에서 해당 스킬의 룰을 먼저 확인한다.

- 같은 스킬을 반복 수정하면서 같은 패턴 실수가 재발하는 것을 막기 위함이다 (세션·파일명 하드코딩, 절차 분기 패턴 등).
- 특화 체크리스트가 있으면 그 항목을 사전 점검표로 쓰고, 없으면 일반 `/scw` 절차(「프롬프트 감사」)를 적용한다.
- 수정 후에만 점검하면 위반이 산출물에 들어간 뒤에 잡히므로, 사전 참조 흐름이 더 효율적이다.

## 프롬프트 수정 시 감사 규칙 역제안

이 프로젝트의 프롬프트(`deploy/`) 수정 시:

1. 요청된 수정을 수행
2. 패턴성 판단 (동일 요청 재발 가능성 — 전환 문장, 이모지, 중복 병기 등)
3. 패턴성이면, scw의 특화 체크리스트(`local/skills/scw/specialized/`)에 추가할 규칙을 구체적 문안과 함께 역제안

## 프롬프트 작성 원칙

- 구체적인 개수를 본문에 하드코딩하지 않는다.
- 프롬프트를 추가하기 전에, 더 강한 강제 메커니즘으로 내릴 수 있는지 먼저 검토하고 사용자에게 역제안한다. 도메인에 따라 사다리가 갈린다.
  - **코드 컨벤션**(네이밍·스타일·타입 등): 정적분석(SwiftLint·SwiftFormat·Tuist 그래프 검사) → hook → 프롬프트 순으로 시도한다. 정적분석은 사람·CI·타 도구 어디서나 걸리고 hook은 에이전트 런타임 안에서만 발동하므로, 코드 규칙은 정적분석이 우선이다.
  - **에이전트 행동·채팅 인터셉트**(매 턴 교정·컨텍스트 주입 등): 정적분석 적용 불가. hook(예: UserPromptSubmit 주입) → 프롬프트 순으로 시도한다.
  - 판단 기반 행동(맞춤법·표현 교정 등)은 기계 판정이 불가능하다. hook은 *발동*만 보장하고 동작은 여전히 LLM이 수행한다는 한계를 인지하고 선택한다.
- 입력 타입 조합 규칙을 추가할 때는 트리거 지점(어느 가이드의 어느 단계에서 판단하는지), 실행 경로(선행 조건이 충족되는지), 판단 기준(어떤 입력이 조합을 활성화하는지)을 함께 정의한다.
- 단방향 cross-ref 원칙: A가 B를 참조하면 B는 A의 식별자(이름·경로)를 본문에 호명하지 않는다. 양방향 결합은 작성 시점에 금지. 호출자는 호출 컨텍스트 쪽, 참조 대상은 일반·재사용 가능한 쪽(컨벤션·메타 룰).

## 프롬프트 수정 후 자가점검

md 파일 수정 직후:

1. 변경된 식별자 식별 — 헤딩 이름, 룰 명칭, 인용된 경로(파일·라인), 절 이름
2. 각 식별자로 워크스페이스 grep
3. 참조처에서 stale 표현 잔존 점검
4. 발견 시 수정하거나 사용자에게 보고

이름·식별자가 안 바뀌어도 룰 본문이 의미 변경되면 cross-ref하는 위치의 정합성도 점검.

## 배포 시스템 수정 규약

배포·hook 인프라는 Python으로 포팅되어 있다. 다음을 수정·추가할 때는 `Makefile` 타겟과 `scripts/` 하위 Python 스크립트를 진실 원천으로 본다.

- `scripts/sync_*.py`·`unsync_*.py` 또는 `make sync-*`·`make unsync-*` 타겟
- `deploy/hooks/`(전역)·`local/hooks/`(로컬)의 정책 hook
- `deploy/base-settings.json`·`local/base-settings.json` 등 settings 생성 소스
- settings.json의 PreToolUse/PostToolUse hook
- `make install-hooks`가 설치하는 git `commit-msg` hook(`scripts/commit_msg.py`)
- 작업용 worktree 생성

새 동기화 대상을 추가할 때는 같은 변경 안에서 `Makefile`에 `sync-<target>`·`unsync-<target>` 타겟과 `scripts/sync_<target>.py`·`scripts/unsync_<target>.py`를 함께 등록하고, `meta/guides/<target>.md`에 수행 작업·제거 기준·반복 실행 기준을 적는다.

## 로컬 스킬 원본 기준

- 프로젝트 로컬 스킬의 원본은 `local/skills/`이다.
- `.claude/skills/`(Claude가 읽음)와 `.agents/skills/`(Codex가 읽음)는 `local/skills/`에서 배포된 산출물로 간주한다 (gitignore).
- 로컬 스킬을 수정해야 하면 산출물(`.claude/skills/`·`.agents/skills/`)을 직접 수정하지 않고 `local/skills/` 원본을 수정한 뒤 배포한다.
- 전역 스킬은 `deploy/`에서 Claude와 Codex 타겟으로 함께 배포되므로 이 제약과 구분한다.

## 폴더 규칙

### 소주제 (이 레포 안에서 어디로)

- `deploy/rules/` — 전역 AI 행동 규칙
- `deploy/skills/` (전역 배포) / `local/skills/` (이 레포 로컬) — 「로컬 스킬 원본 기준」 참고
- `deploy/contexts/` 하위 → 각 디렉토리의 `map.md` 역할 섹션 (「contexts 하위 디렉토리 관리」 참고)

## contexts 하위 디렉토리 관리

- `deploy/contexts/` 하위에 `map.md`가 있는 디렉토리는, 파일을 추가·삭제·이동할 때 `map.md`를 함께 갱신한다
- 내용을 추가·수정·삭제할 때 `map.md` 상단의 "역할" 섹션을 확인하고 적합한 위치에 배치한다
