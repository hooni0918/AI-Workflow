# Step 2: 과제 정의 + 구현 방침

> **이 단계의 목표: 과제를 정의하고("무엇") 그 구현 방침을 상세화한다("어떻게").**

> **Plan mode 필수.** AI가 제시한 과제·구현 방침은 각각 사용자 승인을 거쳐야 한다. 과제 정의가 승인되기 전에는 구현 방침을 작성하지 않고, 구현 방침이 승인되기 전에는 IMPL 세션으로 넘어가지 않는다.

멀티 PR의 2번째 이후 PLAN(`PLAN 2` 등)은 step-1의 배경·분할을 건너뛰고 `project.md`를 읽어 이 스텝(과제·방침)부터 수행한다. 아래 절차의 `pr{N}`은 현재 작업 중인 PR 번호다.

---

## 파트 A: 과제 정의 (무엇)

### 컨벤션 사전 참조

overview.md 작성 전에 아래를 읽고 기술 전략에 반영한다:

- `/plan/background/retained/conventions-index.md`(step-1 산출물)에서 이번 PR 관련 항목을 **선별**한다. 프로젝트 컨벤션을 여기서 재수집하거나 사용자에게 재질문하지 않는다 — 인덱스에 없는 갭이 의심될 때만 그 갭을 콕 집어 질문한다.
- 인덱스가 없으면 fallback으로 사용자에게 프로젝트별 컨벤션이 있는지 확인하고, 있으면 함께 참조한다.
- 빌드·테스트·`flutter analyze`·codegen·l10n·레이어 검증 명령이 필요하면 [conventions/commands.md](../conventions/commands.md)를 단일 출처로 참조한다.

여기서 선별한 컨벤션 경로는 `/plan/pr{N}/persistent/reference.md`에 초기 작성한다 (외부 자료 링크 + 회사·프로젝트 컨벤션·기존 코드 best-practice 경로 인덱스).

### 기존 코드베이스 유사 패턴 자동 탐색

overview.md 작성 전에, 이번 PR이 만들 화면·로직과 같은 역할을 하는 기존 코드를 탐색한다.

- 기존 Bloc·usecase·Repository·데이터 레이어·재사용 위젯 등에서 같은 패턴을 Glob/Grep으로 찾는다.
- 매칭되는 best-practice 패턴이 있으면 `reference.md`에 **참조 링크(파일 경로 + 라인)**로 기록한다 — 그 위에서 구현한다.
- 매칭이 없으면 사용자에게 어떤 패턴을 따를지 문의한다.

**레퍼런스 채굴 강화**: 유사 기능의 **머지된 PR 2~3개**를 찾아 `reference.md`에 경로 인덱스(파일 + 라인)로 남긴다. 산문 요약이 아니라 "이 화면의 Bloc은 `<경로:라인>`을 따른다" 식의 실물 코드 좌표를 적는다. 근래 머지된 유사 flutter PR을 레퍼런스로 삼는다.

### overview.md 생성 + 기술 전략 수립

`/plan/pr{N}/`과 `/plan/background/`를 탐색하여 기존 산출물을 읽고, overview.md를 작성한다. 이 파트에서는 읽기만 하며 원본을 삭제하지 않는다 (소비·삭제는 파트 B).

이 파트는 "무엇을 구현할지"를 결정한다. "어떻게 구현할지"는 파트 B.

#### 여러 해결방법 비교·검증

overview.md를 **단일 작업 캔버스**로 쓴다. 기술 선택에서 여러 해결방법이 가능하면 후보를 나열한다.

- AI는 결정 후보를 나열하고 각 후보 옆에 비어 있는 trade-off 칸(유리한 축 / 불리한 축)만 만든 뒤 "이 결정의 trade-off를 적어 주십시오"라고 질문한다. AI가 임의로 trade-off를 채우지 않는다.
- 사용자가 채운 trade-off 위에서 AI는 빠진 축·과장된 축을 검증·보강한다.
- 기술 선택 예: 상태 흐름(Bloc 이벤트·상태 설계), `Future` vs `Stream`, 목록 컨테이너(`ListView` vs `CustomScrollView`+Sliver), 화면 전환 방식(`Navigator.pushNamed` 라우트 구성) 등. 구현 어휘는 Flutter 위젯·Bloc을 따른다.

이 파트 종료 직전 각 갈래를 분배한다:

| 갈래 | 분배 대상 |
|---|---|
| 의사결정 근거·트레이드오프·거부 대안·발화 흐름 | `pr{N}/persistent/decisions.md` |
| 외부 자료 링크·기존 코드 best-practice 경로·레퍼런스 PR 인덱스 | `pr{N}/persistent/reference.md` |
| 기술 선택 결과 (채택안) | `pr{N}/persistent/decisions.md` 채택안 절 |
| 의도(목표·범위·열려있는 질문) | `pr{N}/consumable/overview.md` |

### 산출물: `/plan/pr{N}/consumable/overview.md`

**의도 수준만 기술**한다 — 상세 스펙·구체적 기술 키워드(라이브러리명, dp값, 토큰명)·코드 블록은 넣지 않는다. 본 파일의 마지막 소비자는 step-5 (PR 본문 작성).

본문 항목:
- 이 PR의 목표
- 범위 요약 (뭘 만드는지의 경계)
- **열려있는 질문** — 본 PR **외부 의존성** (백엔드 합의·디자인 검수·인프라 결정 등 본 PR 안에서 해소 안 되지만 다른 PR로 옮기지도 않는 항목). step-5에서 PR 본문 "Known issues / Follow-up" 절로 녹임

**PR 이연 항목은 「열려있는 질문」이 아니라 `project.md`의 해당 PR 섹션에 적는다.**

### 의사결정 토론

overview.md 작성 후, 토론할 의사결정 항목을 식별하여 사용자에게 안내한다. 자동으로 토론에 진입하지 않으며, 사용자의 명시적 허가가 있을 때만 진행한다.

- **안내 내용**: 토론 후보 항목 목록 + 항목별 핵심 쟁점 한 줄. 각 후보 옆에 trade-off 칸을 비워두고 사용자가 채우게 한 뒤 토론 진행.
- **방식 (허가 시)**: 반대 입장 에이전트(opus)를 spawn하여 메인 에이전트가 기술 선택을 방어한다. 반대 에이전트는 [/discussion 원칙](../../discussion/SKILL.md) 적용 — 정확성 우선, 모호한 근거 수용 금지.

### [CRITICAL] Project 문서 간소화

`project.md`가 존재하면 현재 PR의 상세 내용을 삭제하고 제목만 남긴다. TODO는 overview.md에 옮기고 사용자에게 안내한다.

### 산출물: `/plan/pr{N}/persistent/decisions.md`

본 스텝에서 초기 작성. 의사결정 흐름(사용자 발화 단계 + 거부/채택 사유). 사용자 발화 인용은 그대로, 코드는 시그니처 수준만.

---

## 파트 B: 구현 방침 (어떻게)

파트 A가 "무엇을 구현할지"를 결정했다면, 이 파트는 "어떻게 구현할지"를 상세화한다. overview.md(의도)·decisions.md(기술 결정·근거)·reference.md(참조 인덱스)를 기반으로 파생 산출물을 생성한다.

### 잔여 산출물 소비

`/plan/pr{N}/`과 `/plan/background/`를 탐색하여 기존 산출물을 읽고 아래 파생 산출물(md)로 분배한다. 소비된 transient 원본은 삭제한다. 단, ① 후속 세션이 진실 원천으로 재독할 `retained/` 자료(`figma-url.md`·`logic-contract.md`·`conventions-index.md`)와 ② 하류 세션이 소비할 consumable(`screen.md`·`overview.md`)은 그 소비 세션까지 삭제하지 않는다.

PLAN은 코드를 작성하지 않는다 — 화면 마크업·로직 코드는 모두 IMPL(step-3)이 처음부터 작성한다. 이 파트의 산출물은 IMPL이 소비할 **구현 브리프(md)**다.

### 구현 컨텍스트 수집

다음 세션에서 Lead가 팀에게 컨텍스트를 주입할 때 산출물에 적힌 경로를 기반으로 분배한다. 따라서 파생 산출물 작성 전에 구현 컨텍스트를 미리 수집한다.

파트 A의 "컨벤션 사전 참조"·"기존 코드베이스 유사 패턴 탐색"을 기반으로 추가 컨텍스트를 질문 수집한다:
- 관련 컨벤션 경로 (파트 A 확인분 외 추가)
- 참조할 기존 코드 경로 (유사 Bloc·usecase·데이터 레이어·재사용 위젯)
- 디자인 토큰 / design_system 경로

선별된 컨벤션·패턴 경로를 `reference.md`에 누적 명시한다.

### [CRITICAL] 컨벤션 1차 소스 직접 grep 의무

파일 배치·네이밍·import 경로·레이어를 결정할 때 관련 컨벤션 1차 소스를 **직접 grep**한 후 결과를 `implementation.md`의 해당 결정 옆에 `// [Convention] <경로>` 인용으로 남긴다. IMPL 구현자는 실제 코드 작성 시 이 인용을 코드 주석에 반영한다. "안다고 가정"·"이전 세션 기억"·"이전 PR에서 본 패턴"에 의존하지 않는다.

**결정 시점 트리거**: 아래 결정을 내리려는 그 순간이 grep 발동 시점이다. 결정·파일 작성 전에 grep 결과를 받아야 한다.

- 파일 경로 후보를 정하는 순간 (패키지/폴더 배치)
- "이전 PR에서 보던 패턴 그대로" 같은 기억 trigger 발화 직후
- **레이어 배치** (어느 패키지에 둘지 — `feature`/`domain`/`data` 단방향 의존 준수). 리뷰에서 가장 자주 지적되는 축이 레이어이므로 이 결정은 특히 grep 없이 넘어가지 않는다
- 사용자 압박 발화("빨리", "그냥 해")로 grep 회피 유혹 시 — 압박은 면제 트리거 아님

대상 컨벤션 1차 소스: 레퍼런스 패키지 코드(`reference.md`의 머지 PR 경로), `analysis_options.yaml`, 각 패키지의 `pubspec.yaml`(레이어 방향 = `dependencies:`의 `path:` 의존), 작업 대상 디렉터리 조상 체인 `CLAUDE.md`, [conventions/review-checklist.md](../conventions/review-checklist.md)(리뷰 채굴 근거, 로컬 전용). `conventions-index.md`가 있으면 거기 등재 경로를 grep 출발점으로 우선한다.

레이어 배치는 각 `pubspec.yaml`의 `path:` 의존을 grep해 방향을 대조한다. 정확한 허용 방향 표는 이 스킬이 단정하지 않는다 — 의도 방향(clean arch: `feature → domain ← data`, domain 최내곽, `core`·`design_system` 횡단)을 기준선으로 두되, 과거 `domain → core` 의존이 leak된 이력이 있으므로 실제 허용 방향은 review-checklist.md의 리뷰 채굴 근거 + 코드베이스 실측으로 확인한다.

사유: 컨벤션 위반은 reviewer가 잡기 전 PLAN 단계에서 막아야 한다. 레이어 역방향 의존은 [conventions/commands.md](../conventions/commands.md)의 레이어 검증(pubspec `path:` grep)이 사후에 잡지만, 사전 grep으로 차단하는 게 비용이 낮다.

### 파생 산출물: `implementation.md`

| 산출물 | 위치 | 형태 | 작성 조건 |
|--------|------|------|---------|
| `implementation.md` | `pr{N}/persistent/` | 구현 순서·커밋 분할·회귀 체크리스트·**테스트 TODO 체크리스트** | 항상 |

- **테스트 TODO는 코드 스켈레톤이 아니라 이 체크리스트로 관리**한다. PLAN은 빈 골조 파일을 만들지 않으며, IMPL이 실제 코드 + 테스트를 처음부터 작성한다. 체크리스트의 각 테스트 TODO는 구현 순서·커밋 분할의 어느 커밋에서 다뤄지는지 매칭해 둔다.
- `implementation.md`는 **IMPL 시작 게이트**의 대상이다 — 사용자 미검토 항목이 남아 있으면 IMPL 진입 불가.
- `markup.md`는 생성하지 않는다. figma 인덱스는 step-1이 수집한 `retained/figma-url.md` 단일이며, figma 시각 대조는 IMPL(UI 증분 A축)과 step-4 게이트에서 이 파일을 기준으로 수행한다.

---

## 종료 시퀀스 (모두 필수, 스킵 금지)

산출물 작성 완료 + 사용자 OK 발화 직후, 브랜치·워크트리 생성 전에 아래 1~4단계와 「산출물 파일 존재 확인」을 순서대로 수행하고, 그 결과를 5.로 보고한다.

### 1. 산출물 리뷰 (Reviewer 팀 에이전트 spawn) [CRITICAL]

파생이 끝나면 리뷰어 팀 에이전트를 spawn한다 (팀 운용은 현재 런타임이 제공하는 에이전트 기능 기준 — Claude Code면 Agent Teams).

```
Lead (메인 세션) — 리뷰 결과 종합 + 사용자 보고
└── Reviewer — 산출물 전체 리뷰
```

리뷰 체크리스트:
- **컨벤션 대조**: 각 산출물 내용 기반으로 관련 컨벤션을 찾아 대조. `reference.md`에 컨벤션 경로가 누적 명시되어 있는지 확인. 레이어 배치 결정에 `// [Convention]` 근거가 붙어 있는지 확인.
- **코드↔narrative 오배치 검출**: md 산출물에 완전한 코드 구현이 들어가 있지 않은지 (decisions.md의 코드는 시그니처 수준만). 컨벤션·레퍼런스는 경로로 인용(`// [Convention]`·`reference.md`)하고 산문으로 장황히 재서술하지 않았는지. 실제 코드는 IMPL이 작성한다.
- **설계 타당성 역추적**: decisions.md 기술 결정·overview.md 의도를 기준으로 `implementation.md`가 충실히 반영하는지.
- **산출물 간 정합성**: overview.md 의도 ↔ decisions.md 채택안 ↔ implementation.md 커밋 계획이 일관적인지. 모든 테스트 TODO가 implementation.md의 어느 커밋에서 다뤄지는지 대조. 테스트는 구현 커밋에 함께 포함.
- **자유 리뷰**.

### 2. 종료 게이트 (테스트 TODO 매칭)

산출물 리뷰와 별개로 직접 수행. implementation.md의 커밋 계획과 테스트 TODO 체크리스트를 매칭/누락/면제로 분류한다. 테스트 TODO가 0건인 PR이면 면제로 분류하고 사유를 명시한다.

### 3. 부정 명시 메아리 자가 점검

SKILL.md 「부정 명시 메아리 자가 점검」을 산출물 전체에 발동. 0건 수렴까지.

### 4. 자가 검토

SKILL.md 「자가 검토 필수」의 셀프 리뷰 적용.

### [CRITICAL] 산출물 파일 존재 확인

보고 전에 산출물 파일이 실제로 생성되었는지 확인한다: overview.md(필수), reference.md(필수), implementation.md(필수), decisions.md(토론했거나 명시 결정이 있는 경우). 구두 보고만으로 완료 처리하지 않는다.

### 5. 보고 내용

- 이 PR의 목표 한 줄 요약 + 핵심 기술 선택과 그 이유
- 주요 trade-off나 열려있는 질문 (있는 경우)
- 파생된 산출물 핵심 요약
- 산출물 리뷰 결과 (1단계) + 종료 게이트 결과 (2단계) + 자가 검토 결과 (3·4단계)

---

## 종료부: 브랜치·워크트리 생성 + IMPL 안내

보고까지 끝나면, IMPL 세션이 커밋을 쌓을 브랜치와 워크트리를 생성하고 다음 세션을 안내한다. 이전 세션의 브랜치를 이어 쓰지 않는다.

- 브랜치명: 신규 기능은 `feature/{짧은-설명}`, 이관/티켓 기반은 `feat/{PLFT-XXXX}/{짧은-설명}`.
- base: 프로젝트 기본 브랜치.
- 워크트리는 프로젝트 루트의 형제 디렉토리에 생성.

IMPL은 이 워크트리에서 base 위에 실제 코드·테스트 커밋을 축적한다. PLAN 산출물(`/plan/` 하위)이 워크트리에 안 보이면, `.gitignore` 대상이면 main repo 절대경로로 그대로 참조하고, 추적 대상이면 base 브랜치에 먼저 커밋해 가져온다.

메인 세션이 직접 cwd를 옮길 수 없으면 사용자에게 워크트리 디렉토리에서 새 세션(`/flutter-workflow IMPL`)을 띄워 이어가도록 안내한다 (SKILL.md 「세션 spawn 안내」).
