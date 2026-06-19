# Tuist 빌드·검증 명령 (단일 출처)

ios-workflow의 step·하위 스킬이 빌드·테스트·정적 검사 명령이 필요할 때 가리키는 단일 출처다. 명령 자체의 전제(Tuist 버전 가정, deprecated 사유, 그래프 검사가 잡는 범위)는 [testing-strategy/assumptions.md](../../../contexts/testing-strategy/assumptions.md)가 진실 원천이다 — 여기서는 워크플로 안에서 어느 명령을 어느 시점에 쓰는지만 정리한다.

## 명령

| 용도 | 명령 |
|---|---|
| 빌드 검증 | `tuist xcodebuild build` |
| 테스트 | `tuist test` |
| 미선언 import 검출 (track A) | `tuist inspect implicit-imports` |
| 의존 그래프 추출 (track B) | `tuist graph` |
| SwiftLint 기계 판정 | `swiftlint lint --strict` |

> `tuist build`는 Tuist 4.x에서 deprecated이므로 쓰지 않는다. 빌드 검증은 `tuist xcodebuild build`로 한다. 이 사실과 버전 가정은 [assumptions.md](../../../contexts/testing-strategy/assumptions.md)에 단일 기재돼 있다.

## 어느 시점에 무엇을

- **로직 검증의 진실 원천**은 `tuist test` 실행 결과다. AI 산출물(테스트 매핑표 등)을 검증 기준으로 쓰지 않는다.
- **stub 커밋 게이트**: stub 커밋 전 `tuist xcodebuild build`와 `swiftlint lint --strict`를 통과시킨다.
- **그래프 검사는 빌드와 별개**: 빌드 통과는 레이어 단방향을 보증하지 않는다. `tuist inspect`(미선언 import)와 `tuist graph`(레이어 위상)는 잡는 대상이 다르므로 둘 다 돌린다. 무엇이 무엇을 잡는지는 [tuist-module/conventions/graph-verify.md](../../tuist-module/conventions/graph-verify.md)가 절차 단일 출처다.

## 영역 한정

`swiftlint --fix` 같은 자동 수정은 본 PR 영역에만 적용한다. 인자 없이 전역 자동 수정하지 않는다 — PR 외 파일을 일괄 변경해 글로벌 룰 「내 작업 외 변경은 커밋하지 않는다」를 위반한다.
