# Step 7: PR 본문 작성

## 준비

`/plan/`에서 이전 PR의 pr-body.md가 있으면 읽고, 섹션 구조·서술 패턴을 맞춘다.

## PR 본문 작성 (`/plan/pr{N}/consumable/pr-body.md`)

PR 본문을 작성한다. 작업 컨텍스트로 `/plan/pr{N}/` 하위의 모든 산출물과 커밋 로그를 전달한다. 특정 파일명을 하드코딩하지 않고 `/plan/pr{N}/`을 탐색하여 존재하는 산출물을 동적으로 참조한다.

PR 본문 구성:
- 무엇을 / 왜 (overview.md 의도 + decisions.md 핵심 결정)
- 변경 요약 (커밋 로그 기반)
- Test plan (user-test-cases.md 재활용 — 빌드·실행은 [conventions/tuist.md](../conventions/tuist.md) 명령)
- Known issues / Follow-up (overview.md 「열려있는 질문」)

작성 후 사용자가 톤·구조·분량을 다듬는다.

## 산출물 정리

PR 본문 작성이 완료되면, `/plan/pr{N}/` 하위의 각 산출물을 PR 본문 및 코드와 대조한다.

- 모든 내용이 PR 본문 또는 코드에 반영된 경우: 해당 파일 삭제
- 아직 반영되지 않은 판단·결정 내용이 남아 있는 경우: 해당 파일 유지
- **`/plan/pr{N}/persistent/` 하위는 정리 대상에서 제외** — 영구 보존 자료. 대조도 수행하지 않는다.

대조는 수행하되, 사용자에게는 삭제·유지 파일 목록(유지 시 한 줄 사유)만 보고한 뒤 삭제한다.

## 2회차 최종 커밋 정리 (마지막 PR 한정)

본 PR이 **마지막 PR**(`/plan/` 하위 가장 높은 번호의 `pr{N}` 디렉토리가 현재 작업 중인 PR)이면, 머지 직전에 전체 PR 커밋 메시지의 `[PR{N}]` 접두사를 제거하고 메시지를 재작성한다. 마지막이 아니면 건너뛴다.

절차:
- 시작 전 백업 브랜치: `git branch backup/<현재브랜치>-<YYYYMMDD-HHmm>`
- 접두사 제거·메시지 재작성 (stub drop·슬라이스 분할은 각 PR Step 6.5에서 완료됐으므로 본 단계는 메시지 정리에 집중)
- 재작성 완료 후 force-push 요청 (백업 브랜치 이름 + `git log` 결과 보고)
