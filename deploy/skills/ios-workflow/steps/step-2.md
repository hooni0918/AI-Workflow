# Step 2: PR 분할 전략 수립

여러 PR로 나뉠 수 있는 큰 작업의 분할 전략을 수립합니다.

---

## 작업 크기 판단

- **작은 작업** (커밋 3개 이하): 이 단계 건너뛰고 다음 단계로
- **큰 작업** (커밋 4개 이상, 또는 여러 도메인 포함): PR 분할 전략 수립

작업이 작다고 판단되면 사용자에게 스킵을 제안하세요.

---

## PR 분할 원칙

- **한 번에 하나의 PR, 하나의 구체적인 기능**만 다룹니다.
- **의존성 순서**: 공통 모듈 → 개별 화면. iOS 모듈 레이어가 있으면 레이어 의존 방향(단방향)을 따른다 — Feature → Domain → Data 식. 레이어 역방향 의존이 생기지 않도록 분할 (spm-module/conventions/deps-verify.md 의 Package.swift dependencies grep 대조가 검증 도구).
- **기술적 과제는 다음 단계에서** — 이 단계는 PR 분할에만 집중
- **stub 시점부터 병렬**: `PR_{N}_PLAN.step-4` 종료 시점에 stub 커밋이 외부 시그니처(public/internal API)를 확정하면, PR_{N+1}_PLAN과 PR_{N}_IMPL을 동시 spawn 가능
- **인프라성 PR → 순차**: SPM 의존성 추가·모듈 셋업 등은 stub 시점 병렬 효과가 작으므로 순차 (이전 PR 머지 후 다음 PR_{N+1}_PLAN spawn). 단 "인프라성이라 stub 불필요"는 디폴트가 아니다 — 의존성·설정·`it.todo`가 코드로 표현 가능하면 stub 대상 (step-4 참조)

---

## 기획 점검 (TODO 식별)

PR 분할 초안 작성 후, 각 PR별로 사용자에게 사전 확인이 필요한 TODO가 있는지 확인한다.

---

## Step 1 폴더 재정비

Step 1에서 생성된 `/plan/pr{N}/` 폴더는 화면 플로우 순서 기준이다. PR 경계가 확정되면 번호가 달라질 수 있다.

- 경계 확정 후 Step 1 폴더(`pr{N}`)를 실제 PR 번호에 맞게 rename/merge한다.
- `project.md`의 "참고 background 파일" 경로도 함께 갱신한다.

---

## 산출물: `/plan/background/consumable/project.md`

PR별로 아래 항목을 포함한다:
- PR 제목
- 범위
- 참고 background 파일
- 기획 확인 필요 사항 (TODO)

---

## 보고 내용

- 총 PR 수와 각 PR 범위 한 줄 요약
- PR 간 의존 순서
- 사용자 판단이 필요한 열린 질문 (있는 경우)

---

## Step 2 종료 — 분기점

step-2는 BG 세션의 마지막 step + 후속 세션 spawn 분기점.

「보고 내용」 출력 직후 SKILL.md 「세션 spawn 안내 메커니즘」 절차를 발동하여 후속 spawn 안내(PR_1_PLAN)를 출력.
