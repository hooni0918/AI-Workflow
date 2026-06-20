---
name: ios-workflow
description: 기획서, 디자인 시안(피그마 URL·캡처 등), 버그 리포트를 iOS PR로 변환하는 워크플로우. 배경 파악 → PR 분할 → 설계(stub 시그니처) → 구현 → 테스트 → PR 본문까지 단계별 진행. iOS 작업의 커밋, PR 작성 시 이 스킬을 사용한다.
argument-hint: <세션 이름> <실무|개인>
---

# iOS 워크플로우

## 목적

기획서, 디자인 시안, 버그 리포트를 iOS(Swift; UI 프레임워크는 프로젝트가 결정) PR로 변환한다.

이 워크플로우의 목표는 컨텍스트 격리로 각 단계의 품질·재현성을 높이는 것이다. 그 위에서 의존성이 허락하는 작업은 겹친다 — 다음 PR 설계와 현재 PR 구현을 겹치고(PR 도미노), 화면 마크업을 PR 작업과 병행하며, 리뷰어를 종류별로 나눠 축을 분리해 돌린다.

> 디자인 시안의 한 형태로 피그마를 다루지만, 이 스킬은 **별도의 figma 연동 도구에 의존하지 않는다**. 자료 입수(BG.step-1.1)는 사용자가 제공한 figma URL·캡처·기획 md 같은 자료를 그대로 받아 `background/retained/`에 저장하는 것이며, figma 전용 도구를 호출해 디자인을 끌어오는 단계가 아니다. MARKUP의 디자인 대조도 사용자 제공 자료(URL/캡처)를 진실 원천으로 쓴다.

## 호출

`/ios-workflow <세션 이름> <모드>`

- 세션 이름 디폴트 `BG`. 모드 디폴트 없음 (사용자가 명시 전달 — 실무/개인 분기 영향이 크므로 디폴트 추론 위험).
- 세션 이름: `BG` / `MARKUP` / `PR_{N}_PLAN` / `PR_{N}_IMPL` / `PR_{N}_WRITING`
- 모드: `실무` / `개인`
- 호출 예: `/ios-workflow BG 실무`, `/ios-workflow MARKUP 개인`, `/ios-workflow PR_2_PLAN 실무`

BG가 후속 세션 spawn 안내를 출력할 때 동일 모드 인자를 그대로 포함한다. 모드 자동 감지(폴더 검사 등) 사용 X.

## 세션

워크플로우 5종 세션. 각 세션은 컨텍스트 격리.

| 세션 | (1) 진입 조건 | (2) 입력 컨텍스트 | (3) 출력 산출물 + 라이프사이클 폴더 | (4) 후속 트리거 | (5) 컨텍스트 처리 | (6) 권장 모델 |
|---|---|---|---|---|---|---|
| **BG** | `/ios-workflow BG <모드>` 호출 (유일 루트) | 사용자 제공 자료 (기획서·요구사항·버그 리포트) | `background/persistent/`: 원본 자료 / `background/retained/`: tech-constraints.md·conventions-index.md / `background/consumable/`: project.md / `pr{N}/consumable/`: screen.md (화면별 분석) | step-1.1 후 → MARKUP, 동일 `<모드>` 인자 / step-2 후 → PR_1_PLAN, 동일 `<모드>` 인자 | 컨텍스트 격리. 세션 종료 시 산출물 자가 검토 | **Opus** — PR 분할이 전 세션의 루트 결정, 오판이 도미노로 전파 |
| **MARKUP** | BG.step-1.1 후, `/ios-workflow MARKUP <모드>` 호출 | (실무) step-1.1 수집 figma·시안 자료 / (개인) 공동 정의 기획 md — 화면·섹션·뷰·컴포넌트 단위 | **디자인 진실 원천 0건 완성 마크업 코드** — UI 프레임워크·파일 네이밍은 프로젝트 프로필 따름(예: UIKit이면 `*ViewController.swift`+AutoLayout, SwiftUI면 `*View.swift`) (메인 산출물) + 입력: (실무) `background/retained/figma-url.md`·`figma/` / (개인) 공동 정의 기획 md | 없음 (PR_{N}_IMPL이 화면 단위 마크업 코드를 그대로 가져감) | 마크업 워크트리 | **Sonnet** (figma URL 기준) / **Opus** (캡처-only·개인) — URL은 노드값이 정답이라 결정론적 번역, 캡처·개인은 디자인을 픽셀/의도에서 역추론 + 자기증명 루프 위험 |
| **PR_{N}_PLAN** | (N=1) BG.step-2 / (N≥2) BG.step-2 + (PR_{N-1}이 stub 만든 경우) PR_{N-1}.step-4 stub, 안 만든 경우 PR_{N-1} 머지 | `background/consumable/project.md` 해당 PR 섹션 + BG 산출물 + 이전 PR `persistent/` | `pr{N}/persistent/`: decisions.md, reference.md, **implementation.md** / `pr{N}/retained/`: markup.md (UI 컴포넌트 PR만, 개인 제외) / `pr{N}/consumable/`: overview.md | step-4 stub 만든 경우 → PR_{N+1}_PLAN + PR_{N}_IMPL 동시 spawn / stub 안 만든 경우 → PR_{N}_IMPL만 spawn | PR_{N} 워크트리. 학습 인수인계 후 진입 대기 적용 | **Opus** — stub 시그니처가 다음 PR의 공개 계약, 오판 시 도미노 오염 |
| **PR_{N}_IMPL** | PR_{N}_PLAN.step-4 종료 (필수) + (화면 코드 포함 PR이면) MARKUP의 해당 화면 코드 (필수) + (PR_{N-1}이 stub 만든 경우) PR_{N-1} stub 시그니처 확정 (필수) | implementation.md, markup.md, MARKUP 화면 코드, decisions·reference | 코드 변경 + 커밋 (로직 stub 위에 본체 채움; 마크업은 MARKUP 완성본 import) / `pr{N}/consumable/`: review.md, user-test-cases.md | step-5 끝 후 → PR_{N}_WRITING | PR_{N} 워크트리. 본 PR 하나에 집중 | **Sonnet** (PLAN이 방침 확정 시) — PLAN이 알고리즘 판단을 미뤘으면 Opus |
| **PR_{N}_WRITING** | PR_{N}_IMPL.step-5 종료 | implementation.md + 커밋 로그 + decisions.md + reference.md + `pr{N}/consumable/` 잔여 산출물 | `pr{N}/consumable/pr-body.md` (작성 후 PR 본문 복사 → 폐기) / overview.md 폐기 / `pr{N}/persistent/`는 제외 (영구 보존) | step-7 끝 후 → PR_{N} 머지 안내. 머지 후 PR_{N+1}_PLAN spawn 안내 (PR_{N}이 stub 안 만든 경우) | 구현 맥락 없이 파일 기반으로 PR 본문 작성 | **Opus** — 구현 맥락 없이 파일만 보고 사용자 의도를 추론, 의도 오독 비용 큼 |

(6) 권장 모델은 **세션 구동 모델**이다. MARKUP·IMPL이 내부에서 spawn하는 reviewer 서브에이전트는 impl-review-loop의 자체 모델 분할(기계적 대조=Sonnet/Haiku, 깊은 품질 판단=Opus)을 따른다 — 본 칸과 별개.

### 의존성 그래프

```
BG.step-1.1 ──→ MARKUP
BG.step-2 ────→ PR_1_PLAN

PR_{N}_PLAN.step-4 stub 만든 경우 ──┬─→ PR_{N+1}_PLAN (도미노)
                                    └─→ PR_{N}_IMPL ──(step-5 끝)──→ PR_{N}_WRITING ──(step-7)──→ PR_{N} 머지
PR_{N}_PLAN.step-4 stub 안 만든 경우 ──→ PR_{N}_IMPL ──→ PR_{N}_WRITING ──→ PR_{N} 머지 ──→ PR_{N+1}_PLAN

PR_{N}_IMPL은 MARKUP 워크트리의 검증된 화면 마크업 코드를 그대로 가져옴 (재작성 X).
```

실무와 개인은 그래프가 동일하다. 차이는 MARKUP의 디자인 검사뿐 — figma 대조 대신 사용자 시각 확인([impl-review-loop.md](impl-review-loop.md) 참조).

### 세션 spawn 안내 메커니즘

각 세션의 끝·분기점 step에서 위 「세션」 표를 참조해 후속 spawn 안내를 출력한다 (본문에 후속 세션 명단을 박지 말 것 — 표 갱신이 단일 소스).

**분기점 시점 인식**: 자기 세션의 표 (4) 컬럼에 적힌 "step-X 후" 같은 트리거 step이 분기점이다. 그 step 종료 즉시 본 절차를 발동 — 같은 세션 안 다음 step·분석성 출력·산출물 작성을 본 절차 전에 시작하지 않는다.

**분석 욕구 가드**: 분기점 step 종료 시점에 분석할 자료가 잔뜩 있어도(시안 정독, cross-analysis 등) spawn 안내를 먼저 출력한다.

종료 시 LLM 절차:
1. 표에서 자기 후속 명단 추출
2. 각 후속의 선행 분해 — 자기 선행·방금 끝낸 step은 ✓, 병렬 세션 종료 항목은 미충족 가능 단서로 표시
3. 후속별 spawn 가능 조건 안내 출력 (`/ios-workflow <세션> <모드>` 인자 포함). 표 (6) 권장 모델도 함께 출력. MARKUP은 입력 모달리티(figma URL이면 Sonnet / 캡처-only·개인이면 Opus)에 따라 분기 안내
4. 후속 spawn 안내 출력 직후, "이 세션은 종료되었습니다. 회고가 필요한 시점에 `/pre-exit` 호출하세요." 한 줄 안내

## 구조

- 각 step은 조건에 해당하는 **하위 스킬을 모두 로드**하는 오케스트레이터이거나, 그 자체가 실행 로직
- 해당 스킬이 여러 개이면 **순서대로 하나씩** 실행한다 (동시 로드 불가)
- 각 step의 **산출물이 다음 step의 입력** — step마다 "참고 자료"로 입력 산출물이 명시되어 있음
- 하위 스킬은 워크플로우 세션의 절차 안에서만 호출된다 (독립 호출 없음). 예: MARKUP은 step 없이 본문에서 impl-review-loop를 호출
- MARKUP은 step 번호가 없는 세션 — 본문은 [impl-review-loop.md](impl-review-loop.md)를 디자인 충실도 축으로 호출하는 절차로 구성된다

## /plan/ 폴더 구조

폴더 트리·라이프사이클 규칙(persistent/retained/consumable 동작): consumable은 소비 후 폐기, retained는 세션 간 유지, persistent는 영구 보존. 피그마 URL·캡처는 `background/retained/`에 단일 누적한다.

## 작업 진행 순서

각 세션의 step 매핑. MARKUP은 step 없이 세션 본문([impl-review-loop.md](impl-review-loop.md) 호출)으로 진행한다.

### BG (Step 1~2)

| 단계 | 내용 |
|------|------|
| [step-1.md](steps/step-1.md) | 배경 파악 및 문제 정의 (1.1 자료 받기 / 1.2 requirement-review 본체) |
| [step-2.md](steps/step-2.md) | PR 분할 전략 수립 |

### PR_{N}_PLAN (Step 3~4)

| 단계 | 내용 |
|------|------|
| [step-3.md](steps/step-3.md) | 과제 정의 |
| [step-4.md](steps/step-4.md) | 구현 방침 상세화 + stub 커밋 (stub 시그니처) |

### PR_{N}_IMPL (Step 5~6)

| 단계 | 내용 |
|------|------|
| [step-5.md](steps/step-5.md) | 구현 |
| [step-6.md](steps/step-6.md) | 최종 점검 (테스트·리뷰) |

### PR_{N}_WRITING (Step 7)

| 단계 | 내용 |
|------|------|
| [step-7.md](steps/step-7.md) | PR 본문 작성 |

## [CRITICAL] 지킬 원칙

### 기억 의존 금지
- 각 단계 시작 전 직전 산출물 다시 읽기
- 기억 의존 금지, 파일 현재 상태 기준으로 진행

### 단계별 승인 대기
- 각 단계 완료 후 **반드시 사용자 승인** 후 다음 단계

### 검증 기준 = 진실 원천

리뷰·검증 단계의 기준은 항상 진실 원천(figma 원본 URL, 컨벤션 1차 소스, 테스트 실행 결과, 사용자 발화 등)이다. **AI 산출물(matching 표, 산출물 md 등)을 검증 기준으로 쓰지 않는다.**

이유: AI 산출물은 작성 시점에 누락·오류가 있을 수 있다. 같은 AI 또는 같은 추출 패턴의 Reviewer가 그 산출물을 기준으로 코드를 검증하면, Implementer가 추출 시 놓친 항목을 Reviewer도 못 잡는다. 자기증명 루프.

AI 산출물의 역할은 **Implementer 캐시·인덱스**로만 한정한다. Reviewer 절차에는 진실 원천 직접 fetch·실행을 명시한다.

적용 사례:
- MARKUP의 Figma Reviewer는 `figma-url.md`의 URL로 figma 원본을 직접 fetch해 마크업과 대조 (매칭표는 캐시 보조). 개인 모드는 figma가 없어 사용자 시각 확인이 진실 원천
- 로직 검증의 진실 원천은 프로젝트 테스트 명령 실행 결과 (명령은 프로젝트 프로필이 정의 — 예: `swift test` / `xcodebuild test`, [conventions/spm.md](conventions/spm.md))
- Coding-Standards Reviewer는 컨벤션 1차 소스 파일을 직접 읽음 (`reference.md`는 경로 인덱스 역할). 린터는 기계 판정으로 프로젝트가 정의한 명령을 직접 실행 (예: `swiftlint lint --strict`)

### step 진입 시퀀스

각 세션·step 진입 시점에 다음을 **순서대로** 수행한다. SKILL.md만 보고 자기 지식·기억으로 진행하지 않는다.

1. **해당 step.md 전체를 즉시 Read** — 「작업 진행 순서」 표에서 자기 세션의 step 파일 경로를 찾아 처음부터 끝까지 읽는다.
2. **도입부 [CRITICAL]·필수 절차 실행** — Plan mode 진입 / 컨벤션 사전 참조 / 입력 산출물 탐색 / 사용자 질문 등 명시 절차를 먼저 실행.
3. **사용자 질문 절은 건너뛰지 않는다** — "이미 알고 있다"·"입력 산출물에서 추정 가능"으로 자기 면제 금지.

산출물 작성 시점이 아니라 **step 진입 시점이 step.md Read 트리거**다.

### 사용자 강도 표현 가드

사용자 발화에 강도·범위 강조 표현이 등장하면 (예: "풀로", "전부 다", "빠짐없이", "엄격하게", "꼼꼼히") 이는 **AI의 1차 후보 범위가 부족할 수 있다는 신호**다. AI가 더 큰 1차 소스로 재검증할 것을 요구하는 발화로 해석한다.

발동 절차:
1. 컨벤션 1차 단일 소스(`conventions-index.md` → 매칭 항목 → 컨벤션 본문)를 즉시 Grep·Read
2. 1차 소스에서 발견한 항목이 AI 1차 후보보다 많으면, **추가 항목을 사용자에게 자동 제안**
3. 추가 항목이 PR 범위 안인지 사용자 확인 후 implementation에 반영

자기 면제 금지: 사용자는 1차 후보 자체의 완전성을 검증할 수 없으니 강도 표현으로 위임한 것.

### Plan mode 강제 진입

step.md 도입부에 "**Plan mode 필수**" 표기가 있는 step(step-3·step-4)에 진입할 때 EnterPlanMode 도구를 명시 호출한다. 진입 시퀀스 1순위. 사용자의 짧은 OK 발화("ㅇ", "좋아", "ok")는 plan mode 면제 트리거가 아니다.

### step 종료 시퀀스 미스킵

각 step 본문의 종료 절을 **모두** 실행한다. 산출물 작성 흐름이 끝났다고 종료 시퀀스가 자동 발동되지 않는다.

특히 빠뜨리기 쉬운 절차:
- **Reviewer 팀 에이전트 spawn** — 산출물 OK 발화는 reviewer 진입 트리거지 종료 트리거 아님.
- **부정 명시 메아리 자가 점검** (아래)
- **자가 검토** (아래)

### 자가 검토 필수

각 세션 경계에서 산출물을 2단으로 검증한다.

- **세션 종료 시 셀프 리뷰**: 그 세션에서 생성·수정한 산출물 파일을 검증 소스와 1:1 대조한다. 핵심 명세(Figma 명세 같은 1차 입력)는 모든 항목(트리거 / 방향 / 크기 / 간격 / 토큰 등)을 한 줄씩 ✓/누락 표기.
- **다음 세션 시작 시 외부 검증**: 새 세션이 진입하면 이전 세션의 산출물을 외부 시각으로 한 번 더 검증한다.
- 같은 세션 안의 step 전환에는 적용하지 않는다.
- 산출물 파일이 없는 세션(코드 작업 위주의 IMPL)은 reviewer 파이프라인이 검증을 담당.
- 보고 형식: 이슈 없으면 "자가 검토 통과" 한 줄. 이슈 발견 시 "검토 중 X 발견 → 수정 완료".

### 부정 명시 메아리 자가 점검

산출물 저장 직후, 보고 전에 점검한다. 사용자가 부정 지시("X 쓰지 마")한 항목을 산출물에 메아리("X 안 쓴다")로 다시 적었는지 확인. **사용자가 적지 말라고 한 모든 것을 적지 않는 게 디폴트**.

절차:
1. 산출물에서 부정 표현 라인을 찾는다.
2. 분류: 사용자 메아리(삭제) / 자체 판단 + 명시 근거 동반(유지) / 자체 판단인데 근거 없음(삭제·보강)
3. 1건이라도 있으면 처리 후 재실행. 0건이거나 모두 근거 동반일 때 종료.

**판정 우선순위**: 룰 정신을 우선한다. "발화 원문이라 인용일 뿐"으로 자기 면죄 금지.

### 입력 산출물 비판적 검토

세션·step 진입 시 입력 컨텍스트로 받은 **AI가 만든 결정·narrative 산출물**을 그대로 수용하지 않고 비판적으로 검토한다.

- **대상**: 「세션」 표 (2) 입력 컨텍스트의 AI 결정·narrative만. figma·코드·테스트 결과·사용자 발화는 제외 (「검증 기준 = 진실 원천」 담당)
- **범위**: 자기가 참조·재사용·확장하는 부분에 한정
- **기준**: 자기가 이미 로드한 컨벤션 + 보안·성능·정확성
- **발견 시 처리**: 사용자에게 보고. AI 단독 폐기·수용 금지 — "이전 세션 결정 X에 우려 Y 발견 → 어떻게 진행할지 결정 필요" 식 결정 위임 형태로 출력

### 선행조건 자가체크
- 각 step은 `/plan/`을 탐색하여 이전 단계 산출물과 맥락을 스스로 파악한다.
- 필요한 맥락이 부족하면 사용자에게 질문한다
- 이전 step을 거치지 않고 진입해도 자연스럽게 대응 (step 스킵 허용)

### AI 패턴
- 먼저 생각 제시 → 사용자 의견 구하기 (멈추고 대기)
- 정보 부족 시 역질문

### 학습 인수인계 후 세션 진입 대기 (PR_{N}_PLAN 한정)

- step-1의 "작업 익숙도 판별"에서 인수인계 문서가 작성되었으면, **PR_{N}_PLAN 진입 안내** 시 "사용자가 인수인계 문서 학습을 완료한 뒤 진입하라" 조건을 함께 안내한다.
- 학습 완료 여부를 확인하지 않은 채 진입을 단정적으로 권하지 않는다.
- 인수인계 문서가 없으면 적용되지 않는다.
- 적용 범위: PR_{N}_PLAN만. IMPL·WRITING은 PLAN 결정을 따라가는 작업이라 사용자 학습 결과 직접 필요 X.
