# Step 3: 구현

> **이 단계의 목표: 팀을 spawn하고 구현 방침에 따라 코드를 작성한다**

Lead(메인 세션)가 팀을 구성하고, Feature Implementer가 코드를 작성한다. 커밋마다 리뷰 파이프라인을 수행한다. UI(widget/page)도 로직과 함께 이 세션에서 구현한다.

PLAN(step-2)이 만든 산출물(`implementation.md`·`decisions.md`·`reference.md`·`overview.md`)은 초안이다. 구현 시 계획을 비판적으로 검토하고, 더 나은 방법이 있거나 계획에 문제가 있으면 사용자에게 보고한다 (SKILL.md 「입력 산출물 비판적 검토」).

---

## Step 3.0. 워크트리 진입

PLAN(step-2)에서 만든 워크트리에서 작업한다. 워크트리·브랜치를 새로 만들지 않는다.

- PLAN이 만든 워크트리에서 IMPL 커밋을 base(기본 브랜치) 위에 축적한다.
- 모든 증분 사이클 종료 후에도 IMPL/리뷰 수정 커밋이 그대로 보존된 상태로 step-4에 진입한다. 커밋 정리·재정렬은 step-4에서 **AI 리뷰 + 사용자 리뷰 완료 후** 수행한다 (base→IMPL diff를 사용자가 추적할 수 있어야 함).

메인 세션이 직접 cwd를 옮길 수 없으면 사용자에게 워크트리 디렉토리에서 새 세션을 띄워 이어가도록 안내한다.

---

## Step 3.1. 팀 Spawn

팀 운용은 현재 런타임이 제공하는 에이전트 기능 기준 (Claude Code면 Agent Teams). step-3은 구현자와 리뷰어로 팀을 구성한다. UI 증분이 있고 figma URL이 있을 때만 Design Reviewer를 조건부로 추가한다 (대조형 A의 대조 주체).

```
Lead (메인 세션) — 사용자 소통 + 팀 spawn + Coding-Standards 리뷰 종합
├── Feature Implementer (sonnet) — 로직·UI 구현 + 테스트 작성 + 성능 최적화
├── Coding-Standards Reviewer ×N (sonnet) — 컨벤션 기계적 대조 (`flutter analyze` 직접 실행 포함)
├── Advanced Reviewer (opus) — 코드 품질 판단 + 자유 리뷰
└── Design Reviewer (sonnet) — UI 증분 & figma URL 있을 때만 spawn (구현자와 figma 원본 대조 루프)
```

### Step 3.1.1. Spawn 시 컨텍스트 주입

에이전트는 스스로 컨텍스트를 탐색하지 않는다. **Lead가 필요한 컨텍스트를 주입한다.** Lead는 PLAN 산출물을 탐색하여 분류 후 전달한다.

| 에이전트 | Lead가 주입하는 컨텍스트 |
|----------|--------------------------|
| Feature Implementer | `implementation.md`(구현 순서·커밋 분할·테스트 TODO 체크리스트), 참조할 기존 코드 경로(bloc·usecase·data 등), `reference.md`, 로직·UI 관련 컨벤션, (이관 시) `retained/logic-contract.md` + iOS 원본 소스 경로 |
| Coding-Standards Reviewer ×N | 담당 컨벤션 문서 + [review-checklist.md](../conventions/review-checklist.md) + `analysis_options.yaml`, 리뷰 관점 지시, `reference.md` |
| Advanced Reviewer | [code-review](../../code-review/SKILL.md) 절차, coding standards(flutter 소스 `--coding-standards` 주입), `reference.md`, `implementation.md`의 테스트 TODO 체크리스트 |
| Design Reviewer (조건부) | figma URL(`retained/figma-url.md`), 해당 화면 `screen.md`, 구현 대상 widget/page 경로 |

리뷰어는 [code-review](../../code-review/SKILL.md)의 절차를 따른다. code-review 호출 시 **`--coding-standards`로 flutter 소스를 반드시 명시 주입**한다 — 미주입 시 code-review가 이 스킬과 무관한 기본 폴백 규칙 맵을 로드하므로 금지한다.

### Step 3.1.2. Coding-Standards Reviewer 분할

Lead가 컨벤션 + [review-checklist.md](../conventions/review-checklist.md) + `analysis_options.yaml` + 프로젝트별 컨벤션에서 이번 PR 범위 규칙을 선별하고 주제별로 N개 reviewer를 spawn한다. 분할 단위는 Lead 재량.

---

## Step 3.2. 구현 중 공통 룰

### Step 3.2.0. IMPL 시작 게이트 — 미검토 항목 검사

step-3 진입 직후 step-2 `implementation.md`에 사용자가 미검토한 항목이 있는지 검사한다. 있으면 IMPL 진입 불가.

### Step 3.2.1. gotchas

- **인프라성 PR** — `pubspec.yaml` 의존성·패키지 설정만 추가하는 PR은 Feature Implementer를 spawn하지 않고 Lead가 직접 구현한다. 대상별로 (추가+설정 → 커밋 → 위반 수정 → 커밋) 사이클을 반복. **"팀 spawn 없음"은 Feature Implementer 미spawn을 의미한다. Step 3.3 리뷰 파이프라인(Coding-Standards + Advanced)은 여전히 실행한다.**
- **커밋 분리 디폴트: UI / 로직** — UI(widget/page) 코드와 로직 산출(usecase·bloc·data·테스트·설정)은 다른 커밋으로 분리.
- **커밋 분리 판단: 독립 설명 테스트** — "이 변경을 현재 작업 대상 없이도 독립적으로 설명할 수 있는가?" 가능하면 별도 커밋, 불가능하면 현재 커밋에 포함.
- 새 파일/패키지를 만들기 전에 같은 역할의 코드가 이미 있는지 확인한다. 기존 API·타입·위젯을 재사용할 수 있으면 새로 만들지 않는다.

### Step 3.2.2. IMPL 중 디자인·기획 변경 감지

IMPL 중 디자인 또는 기획이 바뀐 사실을 감지하면 캐시된 산출물을 그대로 두고 진행하지 않는다.

- **디자인 변경** — UI의 진실 원천이 바뀐 것. figma URL이 있으면 변경 단위의 figma 자료를 재수령하고 figma 원본 기준으로 재검증한 뒤 이 세션에서 반영한다. `retained/figma-url.md`도 새 URL로 갱신. figma가 없으면 사용자와 디자인을 다시 정의하고 사용자 시각 확인(hot restart)으로 재검증한다.
- **기획 변경** — 즉시 사용자에게 보고하고 변경 범위를 함께 확정. AI 단독으로 구현 방침·테스트 TODO를 뒤집지 않는다 (SKILL.md 「입력 산출물 비판적 검토」 결정 위임).

### Step 3.2.3. 앱 배선 체크 — `flutter analyze`로 안 잡히는 런타임 배선

신규/이관 기능이 실제로 동작하려면 아래 배선이 필요하며, `flutter analyze`가 못 잡는다 (get_it 런타임 주입은 정적 검사를 통과해도 미등록 시 출시 후 에러까지 발견이 늦다). 구현 중 채워 넣고, Step 3.4 마무리에서 통과를 확인한다.

- 루트 `flutter/pubspec.yaml`에 feature 패키지 등록 (`feature_qube_xxx: path: lib/feature/integration/qube/xxx`).
- 패키지별 `inject.dart`에 get_it 등록 추가 + 상위 inject 체인(`app_initializer.dart`)에 연결. get_it 등록은 `'package:core/inject.dart'`를 사용한다.
- `app_routes.dart`에 라우트 등록 (`Navigator.pushNamed` 대상).
- **MethodChannel 브릿지** (이관 시) — iOS 네이티브 채널 대응을 확인하고, 위치는 **core/platform**에 둔다. 강의실 등 공통 진입은 **ServiceLandingPage 경유**.

배선은 정적 그물이 못 잡으므로 런타임 확인이 필요하다 — `flutter run` 후 **hot restart**로 확인한다 (hot reload는 `main()`/DI/bloc를 재초기화하지 않아 거짓 통과. 명령은 [commands.md](../conventions/commands.md)). 사용자 대상 동작 테스트는 step-4에서 수행한다.

---

## Step 3.3. 리뷰 파이프라인

구현·리뷰는 [impl-review-loop.md](../impl-review-loop.md) 엔진을 호출해 0건까지 수렴시킨다. Lead는 아래 인자를 주입한다. **주입은 세션 단위가 아니라 증분 단위** — 한 PR에 UI·로직 증분이 섞이면 각 증분이 자기 A 메커니즘을 가진다. 두 축의 순서·병렬은 엔진이 A 메커니즘으로 정한다 (대조형(UI)은 A 먼저 0건 수렴 후 B, 오라클형(로직)은 A·B 병렬).

| 증분 종류 | 진실검사 A (메커니즘) | 규칙검사 B (공통) | 증분 단위 |
|---|---|---|---|
| 로직 (usecase/bloc/data) | `flutter test <패키지>` green + 테스트 TODO 커버리지 — **오라클형** | `flutter analyze` 기계 판정 + 아키텍처·레이어 Reviewer(진실원천=레퍼런스 PR 코드 직접 재독 + 각 `pubspec.yaml`의 `path:` 레이어 대조) + 리뷰 체크리스트 Reviewer(진실원천=GitHub 코멘트 원본, [review-checklist.md](../conventions/review-checklist.md)는 캐시) + Advanced 자유 리뷰 | 로직 커밋 |
| 로직-이관 | 위 오라클 + 종료 커버리지 점검을 **iOS 원본 코드 직접 재독**으로 (`retained/logic-contract.md`는 캐시 — 자기증명 루프 차단) | 〃 | 로직 커밋 |
| UI (widget/page) | figma URL 있으면 **Design Reviewer ↔ 구현자 대조 루프**(대조형), 없으면 사용자 시각 확인(hot restart) | 〃 | 화면/컴포넌트 커밋 |

### Step 3.3.1. 증분 사이클 종료

해당 증분의 리뷰 파이프라인이 0건으로 통과하면 그 증분 사이클을 종료한다. **이 시점에는 squash하지 않는다.** 다음 증분 구현 커밋을 이어 쌓고, 모든 증분이 끝난 뒤 step-4에서 일괄 정리한다.

정리 시점은 step-3 안이 아니라 step-4 사용자 리뷰 완료 후 (커밋 이력이 보존돼 diff 리뷰가 가능해야 함).

---

## Step 3 종료 — step-4로 내부 전환

step-3은 IMPL 세션의 첫 step이고, step-4(최종 점검)와 같은 IMPL 세션에 속한다. step-3.4 보고 직후 **즉시 step-4로 진입**한다 — 세션 내부 전환이므로 여기서 후속 세션 spawn 안내를 내지 않는다.

> WRITING 세션 spawn 안내는 IMPL 세션의 분기점인 **step-4 종료**에서 낸다 (SKILL.md 「세션 spawn 안내 메커니즘」). WRITING은 step-4 산출물(최종 커밋·user-test-cases·figma 승인)을 필요로 해 step-4와 겹칠 수 없으므로, step-3 종료에서 조기 발동하지 않는다.

---

## Step 3.4. 마무리

- **테스트 TODO 커버리지 게이트** (IMPL 종료 시점) — `implementation.md` 체크리스트의 모든 테스트 TODO가 실제 test로 전환됐는지 대조.
- **TODO 잔존 점검** — 코드 안 `// TODO:`·`// TODO [AI_IMPL]:` 형태 모두 0건 필수. 잔존 시 종료 불가 (PR 이연·외부 의존성은 `project.md`·`overview.md`로 관리).
- **앱 배선 체크 통과 확인** (Step 3.2.3) — 루트 pubspec 등록·inject.dart get_it 체인·app_initializer·app_routes·(이관 시) MethodChannel·공통 진입.
- Lead가 사용자에게 결과 보고
  - 커밋 목록 (IMPL + 리뷰 수정 커밋, 그대로 보존)
  - 리뷰 결과 요약 (각 단계별 이슈 수 + 해결 내용)
  - **테스트 TODO 커버리지 (전체 todo 수 / 구현된 test 수)**

> [CRITICAL] 이 보고가 끝나도 IMPL 세션은 종료되지 않는다. 즉시 step-4(최종 점검)에 진입한다.
