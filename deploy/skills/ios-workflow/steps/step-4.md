# Step 4: 구현 방침 상세화

> **Plan mode 필수**. Step 3에서 승인된 과제에 대해서만 작성한다.

Step 3이 "무엇을 구현할지"를 결정했다면, 이 단계는 "어떻게 구현할지"를 상세화한다. overview.md(의도)·decisions.md(기술 결정·근거)·reference.md(참조 인덱스)를 기반으로 파생 산출물(stub 코드 + 잔존 md)을 생성한다.

---

## 사전 준비: 브랜치·워크트리 생성

이 단계 시작 시 작업 내용에 맞는 브랜치를 새로 생성하고 워크트리도 함께 만든다. 이전 세션의 브랜치를 이어 쓰지 않는다.

- 브랜치명: `feature/{짧은-설명}` (예: `feature/login-form`)
- base: 프로젝트 기본 브랜치 (main 또는 master)
- 워크트리는 프로젝트 루트의 형제 디렉토리에 생성

이후 이 단계의 모든 작업(stub 파일 생성·stub 커밋)은 새 워크트리 안에서 수행한다. 이전 step 산출물(`/plan/` 하위)이 워크트리에 안 보이면, `.gitignore` 대상이면 main repo 절대경로로 그대로 참조하고, 추적 대상이면 base 브랜치에 먼저 커밋해 가져온다.

메인 세션이 직접 cwd를 옮길 수 없으면 사용자에게 워크트리 디렉토리에서 새 세션을 띄워 이어가도록 안내한다.

---

## 1. 잔여 산출물 소비

`/plan/pr{N}/`과 `/plan/background/`를 탐색하여 기존 AI 산출물을 읽고, **stub 코드(결정·코드 표현 가능 영역)와 잔존 md(narrative)로 분배**한다. 소비된 원본은 삭제한다.

UIKit 화면 마크업(`*ViewController` 레이아웃 시각 구조·디자인 값)은 MARKUP 세션이 디자인 진실 원천 0건으로 완성하므로 **step-4의 stub 대상이 아니다.** 완성 마크업은 MARKUP 워크트리의 **검증된 화면 파일을 그대로 PR 워크트리로 가져온다**(재작성 금지). PR 로직은 가져온 마크업 파일을 **수정하지 않고 별도 파일**(ViewModel·container View 등)에서 주입·합성한다. step-4의 stub 대상은 그 **로직**(ViewModel·UseCase·Repository·테스트·모델·container)이다. (**개인 모드는 figma·markup.md 없음** — 로직·조립 구조 참조만.)

---

## 2. 구현 컨텍스트 수집

다음 세션에서 Lead가 팀에게 컨텍스트를 주입할 때 산출물에 적힌 경로를 기반으로 분배한다. 따라서 파생 산출물 작성 전에 구현 컨텍스트를 미리 수집한다.

Step 3의 "컨벤션 사전 참조"·"기존 코드베이스 유사 패턴 탐색"을 기반으로 추가 컨텍스트를 질문 수집한다:
- 관련 컨벤션 경로 (Step 3 확인분 외 추가)
- 참조할 기존 코드 경로 (유사 ViewModel·네트워크 레이어·재사용 View)
- 디자인 토큰 / 디자인시스템 경로

선별된 컨벤션·패턴 경로를 `reference.md`에 누적 명시한다.

### [CRITICAL] 컨벤션 1차 소스 직접 grep 의무

stub 모듈 구조·파일 배치·네이밍·import 경로·레이어를 결정할 때 관련 컨벤션 1차 소스를 **직접 grep**한 후 결과를 stub 주석 `// [Convention] <경로>` 블록에 인용한다. "안다고 가정"·"이전 세션 기억"·"이전 PR에서 본 패턴"에 의존하지 않는다.

**결정 시점 트리거**: 아래 결정을 내리려는 그 순간이 grep 발동 시점이다. 결정·파일 작성 전에 grep 결과를 받아야 한다.

- stub 파일 경로 후보를 정하는 순간 (모듈/그룹/폴더 배치)
- "이전 PR에서 보던 패턴 그대로" 같은 기억 trigger 발화 직후
- 레이어 배치 (어느 모듈에 둘지 — Feature/Domain/Data 등 단방향 의존 준수)
- 사용자 압박 발화("빨리", "그냥 해")로 grep 회피 유혹 시 — 압박은 면제 트리거 아님

대상 컨벤션 1차 소스: `*ARCHITECTURE*`, `docs/conventions/*`, `Packages/*/Package.swift`, `App.xcodeproj/project.pbxproj`(모듈·의존 정의), 기존 모듈의 평행 사례, 작업 대상 디렉터리 조상 체인 `CLAUDE.md`. `conventions-index.md`가 있으면 거기 등재 경로를 grep 출발점으로 우선한다.

사유: 컨벤션 위반은 reviewer가 잡기 전 PLAN 단계에서 막아야 한다. 레이어 역방향 의존은 [spm-module/conventions/deps-verify.md](../../spm-module/conventions/deps-verify.md)가 사후에 잡지만, 사전 grep으로 차단하는 게 비용이 낮다.

---

## 3. 파생 산출물

| 산출물 | 위치 | 형태 | 작성 조건 |
|--------|------|------|---------|
| stub 파일들 — 로직·조립 View, ViewModel, 테스트, fixture, type 등 (PR이 만들 **외부 공개 모듈은 필수**. 내부 헬퍼는 권장). 시각 마크업은 MARKUP 완성본을 가져오므로 stub 대상 아님 | 소스 디렉토리 | [conventions/stub.md](../conventions/stub.md) 양식 | 항상 |
| `markup.md` | `pr{N}/retained/` | **「Figma 원본 링크 인덱스」 절(사용자 입력)** + 토큰 매핑표 | UI 컴포넌트가 있는 PR이면 필수 (실무). step-6의 사용자 figma 시각 대조 기준. **개인 모드는 figma가 없어 생성 안 함** |
| `implementation.md` | `pr{N}/persistent/` | 구현 순서·커밋 분할·회귀 체크리스트·테스트 TODO 매핑 | 대부분 작성됨 |

---

## 4. stub 파일 작성 룰

stub 파일 작성 룰은 [conventions/stub.md](../conventions/stub.md) 단일 출처. 정의·범위, 디폴트, 양식, 주석, 라이프사이클 모두 본 컨벤션이 담당.

특히 다음 두 가지를 stub.md에서 반드시 확인한다:
- **stub가 보증하는 것 / 못 하는 것**: 시그니처 정합만 컴파일러가 보증하고, 미구현 누락(빈 함수)은 컴파일러가 못 잡는다. 빈 함수는 테스트 오라클·테스트 TODO 커버리지가 잡는다.
- **저장 프로퍼티 초기값은 fatalError로 못 메운다**: 함수 본문은 `fatalError(\"not implemented\")`로 미루지만, 저장 프로퍼티 초기값은 의미 있는 디폴트 또는 placeholder + `// TODO [AI_IMPL]:`로 박아야 컴파일된다.

---

## 5. stub 커밋

### LLM 분석 + 사용자 제안 (PR 번호 무관)

1. **LLM이 PR 작업 분석** — 둘 중 하나라도 해당하면 코드로:
   - **조건 1 (외부 공개 시그니처)**: PR이 만들 public/internal 타입·함수 시그니처 등 외부 공개 모듈.
   - **조건 2 (코드로 표현 가능한 모든 계획)**: 시그니처가 없어도 파일로 표현 가능한 계획은 전부 코드/stub로 — 의존성(SPM `Package.swift` 추가), 설정, 테스트 의도(테스트 TODO). 이들을 어떤 md에도 산문으로 나열하지 않는다.

   **md 산출물 전체**에는 코드로 표현 못 하는 narrative만 남긴다.
2. **사용자에게 제안**: \"이번 PR stub [필요/불필요]. 동의?\" — 조건 2까지 따져 판단.
3. **사용자 동의·수정 후 진행** — stub 만들거나 빈 step-4 (stub 없이 step-5 진입)

**\"인프라성(의존성·모듈 셋업) PR이라 stub 불필요\"는 잘못된 디폴트다** — deps·설정·테스트 TODO가 코드로 표현 가능하므로 조건 2에 의해 stub 대상이다.

### stub 커밋 작성

stub 만들기로 동의되면 모든 stub을 하나의 커밋으로 묶는다.

- 커밋 메시지: `chore: [PR{N}] 초기 골조 stub`
- 이 커밋은 다음 단계의 작업 기반이 되며, 구현이 끝나면 base 위에서 제거된다 ([conventions/stub.md](../conventions/stub.md) 「라이프사이클 > 정리」)
- stub 파일만 담는다 — 잔존 md(`/plan/pr{N}/`)는 별도 커밋. 두 종류를 한 커밋에 섞지 않는다
- stub 커밋이 빌드·SwiftLint를 통과하는지 확인 후 커밋한다: 빌드 오라클, swiftlint ([conventions/spm.md](../conventions/spm.md))

#### [CRITICAL] 포맷팅·SwiftLint 영역 한정

전체 자동 수정(`swiftlint --fix` 인자 없이 전역) 금지. 본 PR 영역만 한정 적용 ([conventions/spm.md](../conventions/spm.md) 「영역 한정」). 사유: 전역 자동 수정은 PR 외 파일을 일괄 변경 → 글로벌 룰 「내 작업 외 변경은 커밋하지 않는다」 위반.

---

## 종료 시퀀스 (모두 필수, 스킵 금지)

산출물 작성 완료 + 사용자 OK 발화 직후, 후속 세션 spawn 안내·보고 출력 전에 아래를 순서대로 모두 수행한다.

### 1. 산출물 리뷰 (Reviewer 팀 에이전트 spawn) [CRITICAL]

파생이 끝나면 리뷰어 팀 에이전트를 spawn한다 (팀 운용은 현재 런타임이 제공하는 에이전트 기능 기준 — Claude Code면 Agent Teams).

```
Lead (메인 세션) — 리뷰 결과 종합 + 사용자 보고
└── Reviewer — 산출물 전체 리뷰
```

리뷰 체크리스트:
- **컨벤션 대조**: 각 산출물 내용 기반으로 관련 컨벤션을 찾아 대조. `reference.md`에 컨벤션 경로가 누적 명시되어 있는지 확인. stub 파일이 빌드·SwiftLint를 통과하는지 확인 (코드라서 가능). stub 작성 룰 준수 ([conventions/stub.md](../conventions/stub.md)) — 저장 프로퍼티 초기값·상태 패턴·throw 패턴 직접 점검.
- **코드-narrative 오배치 검출**: 모든 md에 코드로 표현 가능한 내용(deps·설정·테스트 TODO·시그니처)이 산문으로 들어가 있지 않은지. 있으면 stub 코드로 옮기도록 지적.
- **설계 타당성 역추적**: decisions.md 기술 결정·overview.md 의도를 기준으로 파생 산출물이 충실히 반영하는지.
- **산출물 간 정합성**: stub View의 props 타입을 ViewModel stub이 일관 소비하는지. 모든 테스트 TODO가 implementation.md의 어느 커밋에서 다뤄지는지 대조. 테스트는 구현 커밋에 함께 포함.
- **자유 리뷰**.

### 2. 종료 게이트 (테스트 TODO 매칭)

산출물 리뷰와 별개로 직접 수행. implementation.md의 커밋 계획과 stub의 테스트 TODO를 매칭/누락/면제로 분류. stub 없는 PR이면 테스트 TODO 0건 → 면제로 분류하고 사유 명시.

### 3. 부정 명시 메아리 자가 점검

SKILL.md 「부정 명시 메아리 자가 점검」을 산출물 전체에 발동. 0건 수렴까지.

### 4. 자가 검토

SKILL.md 「자가 검토 필수」의 셀프 리뷰 적용.

### 5. 보고 내용

- 파생된 산출물 핵심 요약
- 산출물 리뷰 결과 (1단계)
- 종료 게이트 결과 (2단계)
- 자가 검토 결과 (3·4단계)
