# Testing Strategy — Assumptions

이 레포가 다루는 iOS 코드의 테스트·CI·검증 전제를 모은 **단일 출처**입니다. 아래 항목은 레포에 실측 설정(테스트 타겟·CI 워크플로·스냅샷 픽스처)이 확정되기 전까지의 **가정**이며, 다른 스킬·규칙 문서는 테스트 전제를 본문에 다시 적지 않고 이 문서를 가리킵니다.

## [CRITICAL] 가정 라벨 규칙

- 아래 "가정"으로 표기된 항목은 실측으로 확정되기 전까지 **단정하지 않는다**. 산출물·리뷰 보고에서 인용할 때 "(가정)" 라벨을 유지한다.
- 가정이 실제 설정으로 확정되면, 이 문서에서 해당 항목을 "확정"으로 승격하고 근거(파일 경로·CI 잡 이름 등)를 함께 적는다.

## 빌드·테스트 명령 (확정)

Tuist 기반 프로젝트의 빌드·테스트 정답 명령:

- 빌드: `tuist xcodebuild build`
- 테스트: `tuist test`

`tuist build`는 Tuist 4.x에서 deprecated이므로 사용하지 않는다. 빌드 검증은 `tuist xcodebuild build`로 한다.

> Tuist 정확한 버전은 (가정) — 레포의 `Tuist/` 설정 또는 `mise`/`.tuist-version` 등으로 확정되면 이 항목에 버전을 박는다. 4.x 계열을 전제로 명령을 적었다.

## 단위 테스트 프레임워크 (가정)

- 단위 테스트는 **XCTest**를 전제로 한다 (가정). Swift Testing(`@Test`) 채택 여부는 레포에 테스트 타겟이 정해지면 확정한다.
- 테스트 타겟 구성(모듈별 `*Tests` 타겟, `Project.swift`의 `.target(product: .unitTests)` 선언)은 (가정) — 실측 후 확정.

## 스냅샷 테스트 (가정)

- 스냅샷 테스트 채택 여부·라이브러리는 (가정). 채택 시 동작 규약:
  - **검증 단계**: 스냅샷 테스트는 **오라클**로 동작한다 — 기준 이미지와 diff가 나면 **fail**. 사람이 개입하지 않는다.
  - **record 단계**: 기준 이미지를 새로 굽거나 갱신하는 record 모드에서만 사람이 개입해 결과를 검토·승인한다.
- 즉, 스냅샷 diff를 "통과로 간주"하거나 검증 단계에서 자동 record로 덮어쓰지 않는다. record는 별도 단계로 분리한다.

## UI 테스트 (가정)

- XCUITest 기반 UI 테스트 채택 여부는 (가정). 채택 시 단위 테스트(XCTest)와 별도 타겟·별도 CI 잡으로 분리한다.

## CI (가정)

- CI 파이프라인(어떤 잡이 `tuist test`를 돌리는지, 스냅샷·UI 테스트가 어느 잡에 묶이는지)은 (가정) — `.github/workflows/` 등 실측 후 확정.
- 정적분석(SwiftLint·SwiftFormat) 잡과 테스트 잡의 분리 여부도 (가정).

## 정적분석과의 경계 (확정 방향)

테스트로 거르기 전에 정적분석이 먼저 거른다 (`deploy/rules/global.md` 「자동화 가능 요청은 메커니즘 역제안」과 같은 사다리).

- 네이밍·스타일·타입 단순 위반 → SwiftLint·SwiftFormat
- 선언하지 않은 import → `tuist inspect`가 잡는다 (이것만)
- 레이어 역방향 의존(단방향 의존 위반) → `tuist inspect`가 아니라 `tuist graph` 해석으로 잡는다
- 위 둘은 서로 다른 검사이므로 혼동하지 않는다.

## stub 검증의 한계 (확정)

stub(시그니처만 만들고 본문은 미구현)으로 구조를 세울 때, 컴파일러가 보증하는 범위와 못 잡는 범위를 구분한다.

- **컴파일러가 보증**: 시그니처 정합(타입·파라미터·반환형·프로토콜 준수). 호출부와 선언부가 맞는지.
- **컴파일러가 못 잡음**: 미구현 누락(빈 함수). 본문이 비어 있어도, 또는 `return` 한 줄만 있어도 시그니처만 맞으면 컴파일된다.
- **`fatalError`로 못 메우는 것**: 저장 프로퍼티와 `@Published` 프로퍼티의 초기값. 함수 본문은 `fatalError("not implemented")`로 스텁할 수 있지만, 저장 프로퍼티·`@Published`는 초기값을 가져야 컴파일되므로 `fatalError`로 미구현을 표시할 수 없다. 따라서 "미구현 프로퍼티"는 컴파일러가 강제로 드러내지 못한다 — 테스트나 리뷰가 잡아야 한다.

## Observation·동시성 전제 (가정)

- `@Observable` 매크로는 **iOS 17+** 한정이다. 배포 타겟이 iOS 17 미만이면 `@Observable`을 전제하지 않는다 (가정 — 레포의 deployment target 실측 후 확정).
- Swift 6 strict concurrency의 "컴파일러 강제"는 **해당 모듈이 strict concurrency mode일 때만** 적용된다 (가정 — `Project.swift`/`Package.swift`의 `swiftSettings`에 `-strict-concurrency=complete` 또는 Swift 6 language mode가 켜져 있는지 실측 후 확정). strict mode가 아니면 데이터 경합 위반은 경고이거나 미검출일 수 있으므로 "컴파일러가 강제한다"고 단정하지 않는다.
