# Stub-as-Contract (단일 출처)

PLAN 단계에서 다음 PR이 기댈 **공개 시그니처만** 먼저 커밋해 두는 stub의 작성 룰이다. stub 시그니처가 다음 PR의 공개 계약이 되어, 다음 PR 설계와 이번 PR 구현을 동시에 굴릴 수 있게 한다.

stub이 무엇을 보증하고 무엇을 못 잡는지(컴파일러 검출 범위, `fatalError`로 못 메우는 자리)는 [testing-strategy/assumptions.md](../../../contexts/testing-strategy/assumptions.md) 「stub 검증의 한계」가 진실 원천이다. 아래는 그 한계를 전제로 한 작성 규칙이다.

## 무엇을 stub으로 세우는가

- 다음 PR이 import할 **외부 공개 모듈의 타입·메서드·프로토콜 시그니처**(필수).
- 모듈 내부 헬퍼(권장).
- 시각 마크업(`*View.swift` 본문)은 stub 대상이 아니다 — MARKUP 세션의 완성본을 그대로 가져오므로.

## 작성 룰

- **함수 본문**: `fatalError("not implemented")`로 비워 둔다. 시그니처(파라미터·반환형·throws·프로토콜 준수)만 정합을 맞춘다.
- **저장 프로퍼티·`@Published` 초기값**: `fatalError`로 미구현을 표시할 수 없다. 컴파일하려면 초기값을 줘야 하므로, 임시값(예: 빈 배열·`false`)을 넣되 **그것이 미구현임을 컴파일러가 드러내지 못한다**는 한계를 안고 간다. 따라서 이 자리는 테스트·리뷰가 미구현 여부를 잡아야 한다(아래 「검증 분담」).
- **관찰 모델 분기**: 상태 객체를 `@Observable`로 세울지 `ObservableObject`로 세울지는 배포 타깃에 달렸다(전제는 assumptions.md 「Observation·동시성 전제」). PLAN에서 정한 쪽을 따른다.
- **접근제어**: 공개 계약이 되는 시그니처는 모듈 노출 수준(`public`/`package`)을 명시한다.

## 검증 분담

- **컴파일러가 보증**: 시그니처 정합(호출부↔선언부 타입 일치). → `tuist xcodebuild build`로 확인([conventions/tuist.md](tuist.md)).
- **컴파일러가 못 잡음**: 빈 함수 본문, 미구현 저장 프로퍼티. → 테스트·리뷰가 잡는다.
- **SwiftLint**: stub 커밋도 `swiftlint lint --strict`를 통과해야 한다([conventions/tuist.md](tuist.md)).

## 라이프사이클

- **생성**: PLAN(step-4)에서 stub 커밋. 다음 PR 설계의 공개 계약 기준이 된다.
- **정리**: 구현이 끝나면 stub 커밋은 base 위에서 제거되고, 그 자리에 본체가 들어온다. IMPL(step-6) 마무리에서 stub 커밋 상태(빈 껍데기 / 본문 안고 있음)에 따라 정리 방식이 갈린다. 케이스별 정리 명령은 step-6 본문이 이 절을 가리킨다.
