> **예시 (참고용).** SwiftUI를 쓰는 프로젝트의 예시다. 마스터 표준이 아니며, 네 프로젝트의 .claude/docs에 네 것으로 정의해 대체하라.

# SwiftUI 작성 규칙 (예시)

SwiftUI로 화면을 짜는 프로젝트가 View 분리·상태 소유·`body` 복잡도·관찰 모델을 어떻게 적는지 보여주는 예시다. 마스터는 UI 프레임워크를 고르지 않으므로, 네 프로젝트가 SwiftUI를 쓰는지·어떤 버전을 타깃하는지는 네 `.claude/docs`(예: `project-profile.md`)가 1차 출처다.

## View 분리 기준

한 `View`의 `body`가 한 화면의 모든 구역을 직접 그리면, 재사용·프리뷰·리뷰 단위가 화면 전체로 묶인다. 다음 신호가 보이면 하위 `View`로 분리한다.

- 같은 구조의 마크업이 두 번 이상 반복된다 → `ForEach` 또는 재사용 `View`로.
- 한 구역이 독립된 입력(데이터·콜백)만으로 그려진다 → 그 입력을 prop으로 받는 `View`로 분리.
- 구역마다 프리뷰를 따로 띄우고 싶다 → 분리해야 프리뷰가 가능하다.

분리한 하위 `View`는 자기에게 필요한 데이터만 받는다. 부모의 전체 상태 객체를 통째로 넘기지 않는다 — 그러면 그 하위 `View`를 부모 없이 재사용할 수 없다.

## body 복잡도 한계

`body`는 "무엇을 그리는가"의 선언만 담는다. 다음은 `body` 밖으로 뺀다.

- 분기·반복 계산, 포매팅, 정렬 같은 로직 → computed property 또는 ViewModel.
- 부수효과(네트워크 호출, 상태 변경) → `.task`/`.onAppear`/액션 클로저 안. `body` 평가 중에 상태를 바꾸지 않는다(렌더 중 mutation은 경고·재진입 위험).

`body` 안에서 직접 `if`/`switch` 중첩이 깊어지면 하위 `View` 또는 `@ViewBuilder` 함수로 쪼갠다.

- **기계 대조(부분)**: SwiftLint `type_body_length`·`function_body_length`·`cyclomatic_complexity`로 길이·분기 과잉을 잡는다. 단 "선언만 담는가"의 의미 판단은 도구가 못 잡으므로 리뷰가 보완한다.

## @State / @Binding 사용 규칙

- `@State`는 그 `View`가 **소유하는** 로컬 상태에만 쓴다. 외부에서 주입받아야 하는 값은 `@State`로 두지 않는다.
- 자식이 부모의 상태를 **읽고 쓰는** 경우에만 `@Binding`을 받는다. 읽기만 하면 일반 `let` 프로퍼티(값 전달)로 받는다 — 불필요한 `@Binding`은 자식이 부모 상태를 바꿀 수 있다는 잘못된 계약을 노출한다.
- `@State` 프로퍼티는 `private`로 둔다. 외부에서 접근할 일이 없는 소유 상태이기 때문이다.
  - **기계 대조**: SwiftLint `private_swiftui_state` 류 커스텀/표준 룰로 `@State`의 `private` 누락을 잡을 수 있다. (가정: 룰 등록 여부는 프로젝트별.)

## 관찰 모델은 도입 환경을 확인하고 쓴다

상태 객체를 `@Observable` 매크로로 만들지, `ObservableObject`/`@Published`로 만들지는 **배포 타깃에 따라 갈린다**. `@Observable`은 iOS 17+ 한정이다.

> Observation·동시성 전제(배포 타깃, 채택 매크로, Swift Concurrency 적용 범위)의 **1차 출처는 네 프로젝트의 `.claude/docs`**(예: `project-profile.md`)다. 그 정의가 있으면 그것을 따르고, 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행한다. 여기서는 모델 선택이 환경에 종속된다는 점만 예시로 보인다.
