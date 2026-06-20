---
name: spm-module
description: SPM 로컬 패키지 기반 iOS 모듈을 추가·재구성한다. 새 패키지(레이어 목록은 프로젝트가 정의) 생성, 기존 모듈 분리·병합, 의존성 추가, 레이어 경계 재정비 요청 시 사용. Package.swift 의존성 그래프 설계와 App 프로젝트 링크 계획을 PLAN 세션에서, 실제 파일 생성·빌드·검증을 APPLY 세션에서 분리 수행한다. '모듈 추가해줘', '이 코드 하위 레이어로 빼줘', '이 화면을 별 패키지로 분리하자', '의존성 정리' 같은 모듈 구조 변경 요청에 사용한다.
argument-hint: "[PLAN | APPLY] [모듈명 또는 작업 대상]"
---

# SPM Module

## 목적

SPM 로컬 패키지 기반 iOS 프로젝트에서 모듈을 추가하거나 재구성한다. (과거 Tuist였으나 SPM 로컬 패키지로 전환한 구조다.)

모듈 작업의 위험은 **"빌드가 성공했다"가 "레이어 규칙을 지켰다"를 보증하지 않는다**는 데 있다. 같은 계층의 모듈이 서로를 직접 import해도, 하위 계층이 상위 계층을 역방향으로 끌어와도(어느 계층이 상위/하위인지는 프로젝트가 정의), 그 의존을 `Package.swift`의 `dependencies` 배열에 선언하기만 하면 컴파일러는 통과시킨다. 빌드 성공은 "선언된 의존 안에서 타입이 맞는다"는 사실일 뿐, 레이어 단방향 규칙 준수와는 별개다.

그래서 이 스킬은 두 세션으로 나뉜다. **PLAN**은 그래프를 먼저 설계하고 `Package.swift` 변경안·링크 계획을 작성한다. **APPLY**는 파일을 생성·빌드한 뒤, 빌드와 독립된 검사(`dependencies` 배열 grep 대조)로 레이어 규칙 준수를 별도 증명한다.

> **용어 정의**
> - **PLAN**: 그래프 설계 세션. 레이어 배치·의존 방향을 정하고 `Package.swift` 변경안과 App 프로젝트 링크 계획을 작성한다. 코드 본체는 만들지 않는다.
> - **APPLY**: 적용 세션. 패키지 디렉토리·소스 스켈레톤을 생성하고 프로젝트 프로필 빌드 오라클로 빌드한 뒤, 레이어 규칙 준수를 검증한다.
> - **레이어**: SPM 로컬 패키지의 의존 계층. 레이어 목록·경계·허용 방향은 **프로젝트의 `layer-rules.json`(기계 대조)·`architecture.md`(산문 정의)가 1차 출처**다 (구체 레이어 목록은 마스터가 고르지 않는다 — 스택별 예시는 `coding-standards/examples`). 단방향·수평 금지·사이클 금지 *방법론*은 [conventions/module-layers.md](conventions/module-layers.md)가 담는다. 둘 다 없으면 사용자에게 묻거나 "가정" 라벨로 진행한다.

## 호출

`/spm-module <세션> <작업 대상>`

- 세션: `PLAN` / `APPLY`. 디폴트 없음 — 사용자가 명시 전달한다. PLAN 산출물(그래프 설계·`Package.swift` diff) 없이 APPLY로 진입하면 검증 기준이 사라지므로 자동 추론하지 않는다.
- 작업 대상: 모듈명 또는 작업 한 줄 요약 (예: `SearchFeature`, `Auth를 화면/도메인/데이터 레이어로 분리` — 레이어 이름은 프로젝트가 정의).
- 호출 예: `/spm-module PLAN SearchFeature`, `/spm-module APPLY SearchFeature`.

PLAN이 종료 시 후속 안내를 출력할 때 같은 작업 대상 인자를 그대로 포함한다 (사용자가 APPLY를 같은 인자로 spawn).

## 세션

| 세션 | 진입 조건 | 입력 | 출력 산출물 | 후속 트리거 | 권장 모델 |
|---|---|---|---|---|---|
| **PLAN** | `/spm-module PLAN <대상>` 호출 | 사용자 요구(추가/분리/병합), 현재 그래프(각 `Package.swift`의 `dependencies`), 프로젝트의 `layer-rules.json`·`architecture.md`(레이어 1차 출처), [conventions/module-layers.md](conventions/module-layers.md)(방법론) | 그래프 설계서 + `Package.swift` diff + App 프로젝트 링크 계획. 코드 본체 없음 | 설계·변경안 사용자 승인 후 → APPLY (`/spm-module APPLY <대상>`, 동일 대상 인자) | **Opus** — 레이어 배치가 후속 의존의 루트 결정. 오판이 그래프 전체로 전파 |
| **APPLY** | PLAN 산출물(그래프 설계·`Package.swift` diff) 확정 + 사용자 승인 | PLAN 설계서, `Package.swift` diff·링크 계획, 대상 모듈 스펙 | `Packages/<New>` 디렉토리·소스 스켈레톤(stub) + 빌드 통과 + 검증 통과(`dependencies` grep 대조) | 검증 통과 후 → 사용자에게 본체 구현 안내 (구현은 이 스킬 범위 밖) | **Sonnet** — PLAN이 그래프·변경안을 확정했으면 정형 생성. 미해결 설계 판단을 PLAN이 남겼으면 Opus |

### 의존성 그래프

```
PLAN (그래프 설계 + Package.swift 변경안 + 링크 계획)
  └─ 사용자 승인 ──→ APPLY (생성 → 빌드 오라클 → dependencies grep 검증)
                      └─ 검증 통과 ──→ 본체 구현 안내 (스킬 범위 밖)
```

PLAN과 APPLY는 컨텍스트를 격리한다. APPLY는 PLAN 설계서를 입력으로 받되, 그 설계를 **검증 기준이 아니라 적용 지시서**로 쓴다 — 검증 기준은 1차 소스인 레이어 규칙(프로젝트 `layer-rules.json`·`architecture.md`, 방법론은 [conventions/module-layers.md](conventions/module-layers.md))과 실제 `Package.swift`의 `dependencies` 배열이다 (「검증 기준 = 진실 원천」 참고).

## 작업 진행 순서

각 세션 진입 시 해당 step 파일 전체를 즉시 Read 한 뒤 진행한다. SKILL.md만 보고 자기 지식·기억으로 진행하지 않는다.

| 세션 | step 파일 |
|------|-----------|
| PLAN | [plan.md](plan.md) — 그래프 설계 + `Package.swift` 변경안·링크 계획 |
| APPLY | [apply.md](apply.md) — 생성 + 빌드 + 검증 |

공통 참조:

- 프로젝트의 `layer-rules.json`·`architecture.md` — 레이어 목록·경계·허용 방향의 1차 출처(스택별 예시는 `coding-standards/examples`)
- [conventions/module-layers.md](conventions/module-layers.md) — 레이어 단방향·수평 금지·사이클 금지 *방법론*. 구체 레이어 목록은 위 프로젝트 파일에 위임
- [conventions/deps-verify.md](conventions/deps-verify.md) — `dependencies` 배열 grep 대조 + 빌드 오라클 검증 절차와 판정 기준

## [CRITICAL] 지킬 원칙

### 빌드 성공 ≠ 레이어 규칙 준수 (자기증명 차단)

빌드는 "`dependencies`에 선언된 의존 안에서 타입이 맞는다"만 증명한다. 다음은 빌드가 통과해도 레이어 규칙 위반이다:

- **레이어 역방향**: 하위 계층이 상위 계층을 의존하도록 `Package.swift`에 선언 → 컴파일은 됨, 단방향 규칙 위반(상위/하위 방향은 프로젝트 `layer-rules.json`이 정의).
- **수평 의존**: 같은 계층의 두 모듈이 서로를 직접 의존하도록 선언 → 컴파일은 됨, 동일 계층 간 격리 위반(격리 대상 계층은 프로젝트가 정의).
- **선언 안 한 import**: 소스에서 import 했으나 `dependencies` 목록에 없음 → 이 경우는 SPM이 컴파일 실패로 잡는다(미선언 모듈 import는 빌드가 막는다).

그래서 검증은 빌드와 **별도 step**으로 둔다. 빌드 통과를 레이어 검증의 근거로 쓰지 않는다. `dependencies`에 역방향·수평 의존을 적으면 컴파일은 통과하므로, **`dependencies` 배열 자체를 레이어 규칙과 grep으로 대조**해야 한다 — 이게 SPM판 "빌드 성공 ≠ 레이어 규칙 준수"다. 빌드 로그·APPLY가 만든 설계서를 검증 기준으로 삼는 것도 금지 — 자기가 작성한 변경안이 규칙을 어겼다면, 그 변경안을 기준으로 한 검사는 위반을 통과시킨다(자기증명 루프). 검증 기준은 항상 레이어 규칙 1차 출처(프로젝트 `layer-rules.json`·`architecture.md`, 방법론은 [conventions/module-layers.md](conventions/module-layers.md))와 각 `Package.swift`의 실제 `dependencies`다.

### 검증은 두 검사가 서로 다른 것을 잡는다

[conventions/deps-verify.md](conventions/deps-verify.md)에 상세. 요약:

- **`dependencies` 배열 grep 대조**: 각 `Package.swift`의 `.package(path:)`·target `dependencies`를 레이어 규칙의 허용 방향과 대조해 **레이어 역방향·수평 의존**을 잡는다. 미선언 import는 보지 않는다(SPM 컴파일이 잡으므로).
- **빌드 오라클(프로젝트 프로필이 정의)**: `dependencies`에 선언 안 한 모듈을 소스가 import하면 SPM이 컴파일 실패로 검출한다. "선언과 소스의 정합"을 본다. 레이어 방향은 보지 않는다(선언만 맞으면 통과).

두 검사는 잡는 대상이 다르므로 **둘 다** 실행한다. 하나만으로 "레이어 검증 완료"라 보고하지 않는다.

### stub은 시그니처 정합만 보증한다

APPLY가 모듈 스켈레톤을 stub으로 만들 때:

- stub은 **공개 타입·함수 시그니처의 정합**만 컴파일러가 보증한다. 시그니처가 맞으면 의존 모듈이 컴파일된다.
- **미구현 누락(빈 함수 본체)은 컴파일러가 못 잡는다.** 본체가 비어 있어도 시그니처만 맞으면 빌드는 통과한다.
- **저장 프로퍼티 초기값**은 `fatalError()`로 메울 수 없다 — 저장 프로퍼티는 초기화가 강제되고, `fatalError`는 함수 본체용이다. stub 단계에서 저장 상태를 가진 타입은 더미 초기값을 박거나, 본체 구현으로 미룬다. "stub이니까 fatalError로 다 막으면 된다"는 가정 금지.
- stub의 빈 본체는 레이어·빌드 검증을 통과시키지만 **기능 검증은 통과시키지 않는다**. APPLY 종료 보고에 "stub은 레이어·시그니처만 보증, 본체 미구현"을 명시한다.

### 단계별 승인 대기

- PLAN의 그래프 설계·`Package.swift` diff·링크 계획은 **사용자 승인 후** APPLY로 넘긴다.
- APPLY는 검증 통과 후 사용자에게 보고하고, 본체 구현은 사용자 판단에 맡긴다 (이 스킬 범위 밖).

### 기억 의존 금지

각 세션 진입 시 직전 산출물(PLAN 설계서·`Package.swift` diff)과 현재 그래프(각 `Package.swift`의 `dependencies`)를 다시 읽는다. 기억이 아니라 파일·도구 출력의 현재 상태로 진행한다.

### 검증 기준 = 진실 원천

검증·대조의 기준은 항상 1차 소스다 — 레이어 규칙은 프로젝트 `layer-rules.json`·`architecture.md`(방법론은 [conventions/module-layers.md](conventions/module-layers.md)), 실제 의존은 각 `Package.swift`의 `dependencies` 배열, 미선언 import는 프로젝트 프로필 빌드 오라클 결과. **AI가 PLAN에서 만든 설계서·변경안을 검증 기준으로 쓰지 않는다.** 설계서는 APPLY의 적용 지시·인덱스 역할로 한정한다.

### 미확정은 "가정" 라벨

다음은 레포·환경마다 다르므로, **프로젝트 프로필/`architecture.md`/`layer-rules.json`이 1차 출처**다. 거기 채워져 있으면 그 값을 따르고, 없으면 사용자에게 묻거나 **"가정"** 라벨로 진행한다. 확인되면 라벨을 떼고 사실로 기록한다.

- **빌드 명령**: 프로젝트 프로필이 정의한 빌드 오라클("이게 통과하면 빌드 OK"의 정답 명령)을 쓴다. 프로필에 없으면 scheme·project 경로를 사용자에게 확인하거나 "가정"으로 표기.
- **테스트**: 테스트 러너 명령과 레이어별 분기(순수 로직 패키지 vs UI 의존 패키지 등), 시뮬레이터 UDID 조회 절차는 프로젝트 프로필의 테스트 명령 슬롯이 1차 출처다. 새 모듈의 구동 방식이 미확인이면 "가정".
- **동시성·언어 모드**: Swift strict concurrency 등 컴파일러 강제 설정은 프로젝트가 정한다. 새로 추가한 패키지에 프로젝트 표준과 동일 설정이 적용됐는지 `Package.swift`에서 확인한다.
- **UI 프레임워크 가용 API**: `@Observable`·SwiftUI 등 특정 API 채택 여부는 프로젝트 UI 프레임워크(프로필)에 달렸다. 미채택 프레임워크 도입을 검토하면 그때 가용성 가정 단서를 단다.
- **정적분석(lint)**: lint 설정 파일(예: SwiftLint/SwiftFormat) 유무는 프로젝트가 정한다. 설정이 없으면 lint 게이트는 **"가정"** 라벨을 유지하고 도입을 역제안할 수 있다 (템플릿: `deploy/templates/swiftlint.template.yml`).
