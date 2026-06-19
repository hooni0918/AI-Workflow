---
name: tuist-module
description: Tuist 기반 iOS 모듈을 추가·재구성한다. 새 모듈(Feature/Domain/Core 등) 생성, 기존 모듈 분리·병합, 의존성 추가, 레이어 경계 재정비 요청 시 사용. 그래프 설계와 manifest 작성을 PLAN 세션에서, 실제 파일 생성·빌드·검증을 APPLY 세션에서 분리 수행한다. '모듈 추가해줘', '이 코드 Core로 빼줘', 'Feature를 분리하자', '의존성 정리' 같은 모듈 구조 변경 요청에 사용한다.
argument-hint: "[PLAN | APPLY] [모듈명 또는 작업 대상]"
---

# Tuist Module

## 목적

Tuist 기반 iOS 프로젝트에서 모듈을 추가하거나 재구성한다.

모듈 작업의 위험은 **"빌드가 성공했다"가 "그래프 규칙을 지켰다"를 보증하지 않는다**는 데 있다. Feature가 다른 Feature를 직접 import해도, Domain이 Feature를 역방향으로 끌어와도, 그 의존을 Tuist manifest에 선언하기만 하면 컴파일러는 통과시킨다. 빌드 성공은 "선언된 의존 안에서 타입이 맞는다"는 사실일 뿐, 레이어 단방향 규칙 준수와는 별개다.

그래서 이 스킬은 두 세션으로 나뉜다. **PLAN**은 그래프를 먼저 설계하고 manifest를 작성한다. **APPLY**는 파일을 생성·빌드한 뒤, 빌드와 독립된 두 검사(`tuist inspect`·`tuist graph`)로 그래프 규칙 준수를 별도 증명한다.

> **용어 정의**
> - **PLAN**: 그래프 설계 세션. 레이어 배치·의존 방향을 정하고 `Project.swift`(또는 `Package.swift`/manifest)를 작성한다. 코드 본체는 만들지 않는다.
> - **APPLY**: 적용 세션. 모듈 디렉토리·소스 스켈레톤을 생성하고 `tuist xcodebuild build`로 빌드한 뒤, 그래프 규칙 준수를 검증한다.
> - **레이어**: Feature / Domain / Core 의 의존 계층. 경계·허용 방향은 [conventions/module-layers.md](conventions/module-layers.md) 단일 출처.

## 호출

`/tuist-module <세션> <작업 대상>`

- 세션: `PLAN` / `APPLY`. 디폴트 없음 — 사용자가 명시 전달한다. PLAN 산출물(그래프 설계·manifest diff) 없이 APPLY로 진입하면 검증 기준이 사라지므로 자동 추론하지 않는다.
- 작업 대상: 모듈명 또는 작업 한 줄 요약 (예: `SearchFeature`, `Auth를 Domain/Core로 분리`).
- 호출 예: `/tuist-module PLAN SearchFeature`, `/tuist-module APPLY SearchFeature`.

PLAN이 종료 시 후속 안내를 출력할 때 같은 작업 대상 인자를 그대로 포함한다 (사용자가 APPLY를 같은 인자로 spawn).

## 세션

| 세션 | 진입 조건 | 입력 | 출력 산출물 | 후속 트리거 | 권장 모델 |
|---|---|---|---|---|---|
| **PLAN** | `/tuist-module PLAN <대상>` 호출 | 사용자 요구(추가/분리/병합), 현재 그래프(`tuist graph` 결과), [conventions/module-layers.md](conventions/module-layers.md) | 그래프 설계서 + manifest diff (`Project.swift` 등). 코드 본체 없음 | 설계·manifest 사용자 승인 후 → APPLY (`/tuist-module APPLY <대상>`, 동일 대상 인자) | **Opus** — 레이어 배치가 후속 의존의 루트 결정. 오판이 그래프 전체로 전파 |
| **APPLY** | PLAN 산출물(그래프 설계·manifest diff) 확정 + 사용자 승인 | PLAN 설계서, manifest diff, 대상 모듈 스펙 | 모듈 디렉토리·소스 스켈레톤(stub) + 빌드 통과 + 검증 통과(inspect·graph 2-track) | 검증 통과 후 → 사용자에게 본체 구현 안내 (구현은 이 스킬 범위 밖) | **Sonnet** — PLAN이 그래프·manifest를 확정했으면 정형 생성. 미해결 설계 판단을 PLAN이 남겼으면 Opus |

### 의존성 그래프

```
PLAN (그래프 설계 + manifest 작성)
  └─ 사용자 승인 ──→ APPLY (생성 → tuist xcodebuild build → 검증 2-track)
                      └─ 검증 통과 ──→ 본체 구현 안내 (스킬 범위 밖)
```

PLAN과 APPLY는 컨텍스트를 격리한다. APPLY는 PLAN 설계서를 입력으로 받되, 그 설계를 **검증 기준이 아니라 적용 지시서**로 쓴다 — 검증 기준은 1차 소스인 [conventions/module-layers.md](conventions/module-layers.md)와 실제 `tuist graph` 출력이다 (「검증 기준 = 진실 원천」 참고).

## 작업 진행 순서

각 세션 진입 시 해당 step 파일 전체를 즉시 Read 한 뒤 진행한다. SKILL.md만 보고 자기 지식·기억으로 진행하지 않는다.

| 세션 | step 파일 |
|------|-----------|
| PLAN | [plan.md](plan.md) — 그래프 설계 + manifest 작성 |
| APPLY | [apply.md](apply.md) — 생성 + 빌드 + 검증 2-track |

공통 참조:

- [conventions/module-layers.md](conventions/module-layers.md) — Feature/Domain/Core 경계와 허용 의존 방향 (레이어 규칙 단일 출처)
- [conventions/graph-verify.md](conventions/graph-verify.md) — `tuist inspect`·`tuist graph` 2-track 검증 절차와 판정 기준

## [CRITICAL] 지킬 원칙

### 빌드 성공 ≠ 그래프 규칙 준수 (자기증명 차단)

빌드는 "manifest에 선언된 의존 안에서 타입이 맞는다"만 증명한다. 다음은 빌드가 통과해도 그래프 규칙 위반이다:

- **레이어 역방향**: Domain이 Feature를 의존하도록 manifest에 선언 → 컴파일은 됨, 단방향 규칙 위반.
- **수평 의존**: FeatureA가 FeatureB를 직접 의존하도록 선언 → 컴파일은 됨, Feature 간 격리 위반.
- **선언 안 한 import**: 소스에서 import 했으나 manifest 의존 목록에 없음 → 이 경우는 보통 링크/빌드 단계에서 잡히지만, transitive 노출로 통과하는 케이스가 있다.

그래서 검증은 빌드와 **별도 step**으로 둔다. 빌드 통과를 그래프 검증의 근거로 쓰지 않는다. 빌드 로그·APPLY가 만든 설계서를 검증 기준으로 삼는 것도 금지 — 자기가 작성한 manifest가 규칙을 어겼다면, 그 manifest를 기준으로 한 검사는 위반을 통과시킨다(자기증명 루프). 검증 기준은 항상 [conventions/module-layers.md](conventions/module-layers.md)(1차 규칙)와 `tuist graph`의 실제 위상이다.

### 검증은 두 도구가 서로 다른 것을 잡는다

[conventions/graph-verify.md](conventions/graph-verify.md)에 상세. 요약:

- **`tuist inspect`**: 소스 파일이 import 하지만 manifest 의존에 **선언되지 않은 import**를 검출한다. "manifest와 소스의 정합"을 본다. 레이어 방향은 보지 않는다.
- **`tuist graph`**: 모듈 간 실제 의존 위상을 산출한다. 이 위상을 [conventions/module-layers.md](conventions/module-layers.md)의 허용 방향과 대조해 **레이어 역방향·수평 의존**을 잡는다.

두 검사는 잡는 대상이 다르므로 **둘 다** 실행한다. 하나만으로 "그래프 검증 완료"라 보고하지 않는다.

### stub은 시그니처 정합만 보증한다

APPLY가 모듈 스켈레톤을 stub으로 만들 때:

- stub은 **공개 타입·함수 시그니처의 정합**만 컴파일러가 보증한다. 시그니처가 맞으면 의존 모듈이 컴파일된다.
- **미구현 누락(빈 함수 본체)은 컴파일러가 못 잡는다.** 본체가 비어 있어도 시그니처만 맞으면 빌드는 통과한다.
- **저장 프로퍼티·`@Published` 초기값**은 `fatalError()`로 메울 수 없다 — 저장 프로퍼티는 초기화가 강제되고, `fatalError`는 함수 본체용이다. stub 단계에서 저장 상태를 가진 타입은 더미 초기값을 박거나, 본체 구현으로 미룬다. "stub이니까 fatalError로 다 막으면 된다"는 가정 금지.
- stub의 빈 본체는 그래프·빌드 검증을 통과시키지만 **기능 검증은 통과시키지 않는다**. APPLY 종료 보고에 "stub은 그래프·시그니처만 보증, 본체 미구현"을 명시한다.

### 단계별 승인 대기

- PLAN의 그래프 설계·manifest diff는 **사용자 승인 후** APPLY로 넘긴다.
- APPLY는 검증 통과 후 사용자에게 보고하고, 본체 구현은 사용자 판단에 맡긴다 (이 스킬 범위 밖).

### 기억 의존 금지

각 세션 진입 시 직전 산출물(PLAN 설계서·manifest diff)과 현재 그래프(`tuist graph`)를 다시 읽는다. 기억이 아니라 파일·도구 출력의 현재 상태로 진행한다.

### 검증 기준 = 진실 원천

검증·대조의 기준은 항상 1차 소스다 — 레이어 규칙은 [conventions/module-layers.md](conventions/module-layers.md), 실제 의존 위상은 `tuist graph` 출력, 미선언 import는 `tuist inspect` 출력. **AI가 PLAN에서 만든 설계서·manifest를 검증 기준으로 쓰지 않는다.** 설계서는 APPLY의 적용 지시·인덱스 역할로 한정한다.

### 미확정은 "가정" 라벨

다음은 레포·환경마다 다르므로, 확인 전에는 **"가정"**으로 표기하고 진행한다. 확인되면 라벨을 떼고 사실로 기록한다.

- **Tuist 버전·명령 형태**: 빌드는 `tuist xcodebuild build`를 정답 명령으로 쓴다 (`tuist build`는 4.x에서 deprecated이므로 쓰지 않는다). 버전이 확인 안 됐으면 "Tuist 4.x 가정"으로 표기.
- **테스트·CI**: 테스트는 `tuist test`. 테스트 타겟 존재·CI 연동 여부가 미확인이면 "가정".
- **Swift 6 strict concurrency**: "컴파일러 강제"는 해당 모듈이 strict concurrency mode일 때만 성립한다. 모듈 설정이 확인 안 됐으면 "strict mode 가정"으로 단서를 단다.
- **`@Observable`**: iOS 17+ 한정 매크로다. deployment target이 그 미만이면 사용 불가 — target 미확인이면 "iOS 17+ 가정".
- **스냅샷 테스트**: 검증 단계에서는 **오라클**(기존 레퍼런스와 diff 시 fail). record(레퍼런스 갱신)는 사람이 개입하는 별도 단계다. 검증 단계에서 record 모드로 돌려 자기 출력을 정답으로 박지 않는다.
