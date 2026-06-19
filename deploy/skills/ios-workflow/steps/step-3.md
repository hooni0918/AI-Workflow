# Step 3: 과제 정의

> **이 단계의 목표: 과제를 정의하고 기술 전략을 수립한다**

> **Plan mode 필수**. AI가 제시한 과제는 사용자 승인을 거쳐야 하며, 승인된 과제만 Step 4에서 구현 방침을 작성한다.

---

### 컨벤션 사전 참조

overview.md 작성 전에 아래를 읽고 기술 전략에 반영한다:

- `/plan/background/retained/conventions-index.md`(자료 수집 단계 산출물)에서 이번 PR 관련 항목을 **선별**한다. 프로젝트 컨벤션을 여기서 재수집하거나 사용자에게 재질문하지 않는다 — 인덱스에 없는 갭이 의심될 때만 그 갭을 콕 집어 질문한다
- 인덱스가 없으면 fallback으로 사용자에게 프로젝트별 컨벤션이 있는지 확인하고, 있으면 함께 참조

여기서 선별한 컨벤션 경로는 `/plan/pr{N}/persistent/reference.md`에 초기 작성한다 (외부 자료 링크 + 회사·프로젝트 컨벤션·기존 코드 best-practice 경로 인덱스).

### 기존 코드베이스 유사 패턴 자동 탐색

overview.md 작성 전에, 이번 PR이 만들 화면·로직과 같은 역할을 하는 기존 코드를 탐색한다.

1. 기존 ViewModel·네트워크 레이어·재사용 View·Repository 등에서 같은 패턴을 Glob/Grep으로 찾는다
2. 매칭되는 best-practice 패턴이 있으면 `reference.md`에 **참조 링크(파일 경로 + 라인)**로 기록한다 — 그 위에서 구현한다
3. 매칭이 없으면 사용자에게 어떤 패턴을 따를지 문의한다

### overview.md 생성 + 기술 전략 수립

`/plan/pr{N}/`과 `/plan/background/`를 탐색하여 기존 산출물을 읽고, overview.md를 작성한다. 이 단계에서는 읽기만 하며 원본을 삭제하지 않는다 (소비는 Step 4).

이 단계는 "무엇을 구현할지"를 결정한다. "어떻게 구현할지"는 Step 4.

#### 여러 해결방법 비교·검증

overview.md를 **단일 작업 캔버스**로 쓴다. 기술 선택에서 여러 해결방법이 가능하면 후보를 나열한다.

- AI는 결정 후보를 나열하고 각 후보 옆에 비어 있는 trade-off 칸(유리한 축 / 불리한 축)만 만든 뒤 "이 결정의 trade-off를 적어 주십시오"라고 질문한다. AI가 임의로 trade-off를 채우지 않는다.
- 사용자가 채운 trade-off 위에서 AI는 빠진 축·과장된 축을 검증·보강한다.
- iOS 기술 선택 예: `@Observable`(iOS 17+) vs `ObservableObject`+`@Published`, NavigationStack vs 기존 라우팅, async/await vs Combine, actor 격리 모델 등.

step-3 종료 직전 각 갈래를 분배한다:

| 갈래 | 분배 대상 |
|---|---|
| 의사결정 근거·트레이드오프·거부 대안·발화 흐름 | `pr{N}/persistent/decisions.md` |
| 외부 자료 링크·기존 코드 best-practice 경로 | `pr{N}/persistent/reference.md` |
| 기술 선택 결과 (채택안) | `pr{N}/persistent/decisions.md` 채택안 절 |
| 의도(목표·범위·열려있는 질문) | `pr{N}/consumable/overview.md` |

### 산출물: `/plan/pr{N}/consumable/overview.md`

**의도 수준만 기술**한다 — 상세 스펙·구체적 기술 키워드(라이브러리명, pt값, 토큰명)·코드 블록은 넣지 않는다. 본 파일의 마지막 소비자는 step-7 (PR 본문 작성).

본문 항목:
- 이 PR의 목표
- 범위 요약 (뭘 만드는지의 경계)
- **열려있는 질문** — 본 PR **외부 의존성** (백엔드 합의·디자인 검수·인프라 결정 등 본 PR 안에서 해소 안 되지만 다른 PR로 옮기지도 않는 항목). step-7에서 PR 본문 "Known issues / Follow-up" 절로 녹임

**PR 이연 항목은 「열려있는 질문」이 아니라 `project.md`의 해당 PR 섹션에 적는다.**

### 의사결정 토론

overview.md 작성 후, 토론할 의사결정 항목을 식별하여 사용자에게 안내한다. 자동으로 토론에 진입하지 않으며, 사용자의 명시적 허가가 있을 때만 진행한다.

- **안내 내용**: 토론 후보 항목 목록 + 항목별 핵심 쟁점 한 줄. 각 후보 옆에 trade-off 칸을 비워두고 사용자가 채우게 한 뒤 토론 진행.
- **방식 (허가 시)**: 반대 입장 에이전트(opus)를 spawn하여 메인 에이전트가 기술 선택을 방어한다. 반대 에이전트는 [/discussion 원칙](../../discussion/SKILL.md) 적용 — 정확성 우선, 모호한 근거 수용 금지.

### [CRITICAL] Project 문서 간소화

`project.md`가 존재하면 현재 PR의 상세 내용을 삭제하고 제목만 남긴다. TODO는 overview.md에 옮기고 사용자에게 안내.

### 산출물: `/plan/pr{N}/persistent/decisions.md`

본 step에서 초기 작성. 의사결정 흐름(사용자 발화 단계 + 거부/채택 사유). 사용자 발화 인용은 그대로, 코드는 시그니처 수준만.

---

## 보고 내용

- 이 PR의 목표 한 줄 요약
- 핵심 기술 선택과 그 이유
- 주요 trade-off나 열려있는 질문 (있는 경우)

### [CRITICAL] 산출물 파일 존재 확인

보고 전에 산출물 파일이 실제로 생성되었는지 확인한다 (overview.md 필수, reference.md 필수, decisions.md는 토론했거나 명시 결정이 있는 경우). 구두 보고만으로 완료 처리하지 않는다.
