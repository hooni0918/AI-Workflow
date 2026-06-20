# Step 5: 구현

> **이 단계의 목표: 팀을 spawn하고 구현 방침에 따라 코드를 작성한다**

Lead(메인 세션)가 팀을 구성하고, Feature Implementer가 코드를 작성한다. 커밋마다 리뷰 파이프라인을 수행한다.

`/plan/pr{N}/`의 산출물(stub 코드 + 잔존 md)은 초안이다. 구현 시 계획을 비판적으로 검토하고, 더 나은 방법이 있거나 계획에 문제가 있으면 사용자에게 보고한다.

---

## Step 5.0. 워크트리 진입

이전 단계에서 만든 워크트리에서 작업한다. 워크트리·브랜치를 새로 만들지 않는다.

- 워크트리에는 stub 커밋이 이미 base 위에 쌓여 있다
- 이 커밋 위에 구현 커밋을 쌓아나간다
- 모든 슬라이스 사이클 종료 후에도 stub 커밋부터 IMPL/리뷰 수정 커밋이 그대로 보존된 상태로 step-6에 진입한다. 커밋 정리·재정렬은 step-6에서 **AI 리뷰 + 사용자 리뷰 완료 후** 수행한다

메인 세션이 직접 cwd를 옮길 수 없으면 사용자에게 워크트리 디렉토리에서 새 세션을 띄워 이어가도록 안내한다.

---

## Step 5.1. 팀 Spawn

팀 운용은 현재 런타임이 제공하는 에이전트 기능 기준 (Claude Code면 Agent Teams). step-5는 로직 구현자와 리뷰어로 팀을 구성한다 — 마크업은 MARKUP 세션에서 검증 완료된 코드를 가져오므로 본 step은 로직 전용이다.

```
Lead (메인 세션) — 사용자 소통 + 팀 spawn + Coding-Standards 리뷰 종합
├── Feature Implementer (sonnet) — 로직 구현 + 테스트 작성 + 성능 최적화
├── Coding-Standards Reviewer ×N (sonnet) — 컨벤션 기계적 대조 (SwiftLint 직접 실행 포함)
└── Advanced Reviewer (opus) — 코드 품질 판단 + 자유 리뷰
```

### Step 5.1.1. Spawn 시 컨텍스트 주입

에이전트는 스스로 컨텍스트를 탐색하지 않는다. **Lead가 필요한 컨텍스트를 주입한다.** Lead는 `/plan/` 하위와 step-4 stub 파일들을 탐색하여 분류 후 전달한다.

| 에이전트 | Lead가 주입하는 컨텍스트 |
|----------|--------------------------|
| Feature Implementer | ViewModel·로직 stub 파일들 (`// TODO [AI_IMPL]:` 포함), 참조할 기존 코드 경로, `reference.md`, 로직 관련 컨벤션 |
| Coding-Standards Reviewer ×N | 담당 컨벤션 문서 + `.swiftlint.yml`, 리뷰 관점 지시, `reference.md` |
| Advanced Reviewer | [code-review](../../code-review/SKILL.md) 절차, coding standards, `reference.md`, stub 테스트의 테스트 TODO |

리뷰어는 [code-review](../../code-review/SKILL.md)의 절차를 따른다.

### Step 5.1.2. Coding-Standards Reviewer 분할

Lead가 컨벤션 + `.swiftlint.yml` + 프로젝트별 컨벤션에서 이번 PR 범위 규칙을 선별하고 주제별로 N개 reviewer를 spawn한다. 분할 단위는 Lead 재량.

---

## Step 5.2. 구현 중 공통 룰

### Step 5.2.0. IMPL 시작 게이트 — TODO 잔존 검사

step-5 진입 직후 본 PR 영역에서 step-4에서 사용자가 미검토한 TODO 항목이 있는지 검사한다. 있으면 IMPL 진입 불가.

### Step 5.2.1. gotchas

- **인프라성 PR** — SPM 의존성·모듈 설정만 추가하는 PR은 Feature Implementer를 spawn하지 않고 Lead가 직접 구현한다. 도구별로 (추가+설정 → 커밋 → 위반 수정 → 커밋) 사이클을 반복. **"팀 spawn 없음"은 Feature Implementer 미spawn을 의미한다. Step 5.3 리뷰 파이프라인(Coding-Standards + Advanced)은 여전히 실행한다.**
- **커밋 분리 디폴트: 마크업 / 그 외** — MARKUP에서 가져온 마크업 코드와 본 step의 로직 산출(로직·테스트·ViewModel·설정)은 다른 커밋으로 분리.
- **커밋 분리 판단: 독립 설명 테스트** — "이 변경을 현재 작업 대상 없이도 독립적으로 설명할 수 있는가?" 가능하면 별도 커밋, 불가능하면 현재 커밋에 포함.
- 새 파일/모듈을 만들기 전에 같은 역할의 코드가 이미 있는지 확인한다. 기존 API·타입·View를 재사용할 수 있으면 새로 만들지 않는다.

### Step 5.2.2. IMPL 중 디자인·기획 변경 감지

IMPL 중 디자인 또는 기획이 바뀐 사실을 감지하면 캐시된 산출물을 그대로 두고 진행하지 않는다.

- **디자인 변경** — 마크업의 진실 원천이 바뀐 것. (실무) 변경 단위의 figma 자료를 재수령하고, MARKUP에서 figma 원본 기준 재검증 후 PR로 다시 가져온다. `markup.md`도 새 URL로 갱신. (**개인 모드**) figma가 없으니 사용자와 디자인을 다시 정의하고, MARKUP에서 사용자 시각 확인으로 재검증 후 가져온다 — markup.md 갱신 단계 없음.
- **기획 변경** — 즉시 사용자에게 보고하고 변경 범위를 함께 확정. AI 단독으로 stub·테스트 TODO를 뒤집지 않는다 (SKILL.md 「입력 산출물 비판적 검토」 결정 위임).

---

## Step 5.3. 리뷰 파이프라인

구현·리뷰는 [impl-review-loop.md](../impl-review-loop.md) 엔진을 호출해 0건까지 수렴시킨다. Lead는 아래 인자를 주입한다. 두 축의 순서·병렬은 엔진이 A 메커니즘으로 정한다.

| 구현자 | 진실검사 A (메커니즘) | 규칙검사 B | 증분 단위 |
|---|---|---|---|
| Feature Implementer | 테스트 실행 green(swift test/xcodebuild test) + 테스트 TODO 커버리지. 오라클형(실행이 곧 판정). | Coding-Standards ×N (SwiftLint 포함) + Advanced (로직 rules) | 로직 커밋 |

### Step 5.3.1. 슬라이스 사이클 종료

해당 슬라이스의 리뷰 파이프라인이 0건으로 통과하면 그 슬라이스 사이클을 종료한다. **이 시점에는 squash하지 않는다.** 다음 슬라이스 구현 커밋을 이어 쌓고, 모든 슬라이스가 끝난 뒤 step-6에서 일괄 정리한다.

정리 시점은 step-5 안이 아니라 step-6 사용자 리뷰 완료 후 (stub→IMPL diff 리뷰 가능해야 함).

---

## Step 5 종료 — 분기점

step-5는 PR_{N}_IMPL 세션의 마지막 구현 step. step-5.4 종료 후 step-6(최종 점검)이 이어진다.

step-5.4 보고 출력 직후, 아래 두 안내를 **즉시** 출력한다 (step-6 완료 후로 미루지 않는다):
1. SKILL.md 「세션 spawn 안내 메커니즘」 발동하여 후속 spawn 안내(**PR_{N}_WRITING**) 출력.
2. 「다음 PR 진입 가능 안내」(PR_{N+1}_PLAN — PR 도미노) 출력.

---

## Step 5.4. 마무리

- 테스트 TODO 매칭 게이트 (IMPL 종료 시점) 적용 — 전체 todo가 구현된 test로 전환됐는지
- **TODO 잔존 점검** — 코드 안 `// TODO:` 형태 모두 0건 필수. 잔존 시 종료 불가 (PR 이연·외부 의존성은 `project.md`·`overview.md`로 관리)
- Lead가 사용자에게 결과 보고
  - 커밋 목록 (stub + IMPL + 리뷰 수정 그대로)
  - 리뷰 결과 요약 (각 단계별 이슈 수 + 해결 내용)
  - **테스트 TODO 커버리지 (전체 todo 수 / 구현된 test 수)**
  - **다음 PR 진입 가능 안내** — 현 PR이 마지막이 아니면 다음 PR의 step-3 진입 가능을 안내 (step-5 종료 = 외부 공개 시그니처 확정). 단 step-6 사용자 리뷰에서 시그니처 변경 시 후속 PR도 영향 — 발생 시 즉시 보고

> [CRITICAL] 이 보고가 끝나도 PR_{N}_IMPL 세션은 종료되지 않는다. 즉시 Step 6(최종 점검)에 진입한다.
