# Coordinator 화면 전환 규칙

> **현재 미채택** — MINO는 Clean Architecture + DDD(UIKit)를 쓰며 Coordinator를 도입하지 않았다. 아래 규칙은 향후 Coordinator 도입 시에만 적용한다. 현재 레이어 경계는 [clean-architecture/layer-rules.md](../clean-architecture/layer-rules.md)가 단일 출처다.

화면 전환의 책임을 `View`에서 분리해 Coordinator에 모은다. 판단 근거·트레이드오프는 [principles/personal/architecture/coordinator.md](../../../principles/personal/architecture/coordinator.md)가 담당하고, 이 문서는 기계 대조 가능한 "~해라/~금지" 규칙만 둔다.

## View는 전환을 직접 수행하지 않는다

`View`/`ViewModel`은 "어디로 갈지" 결정하지 않고 **전환 의도만** Coordinator에 전달한다. 다음을 `View` 안에서 직접 호출하지 않는다.

- `NavigationLink`의 목적지에 다음 화면을 하드코딩, `UINavigationController.pushViewController`, `present`, `dismiss`, `sheet`/`fullScreenCover`의 목적지를 `View`가 직접 구성.

대신 Coordinator가 노출한 메서드(예: `coordinator.show(.detail(id:))`)나 액션 클로저를 호출한다.

```swift
// ❌ bad — View가 다음 화면을 직접 안다
Button("상세") {
    path.append(DetailView(id: item.id))
}

// ✅ good — View는 의도만 전달, 목적지는 Coordinator가 안다
Button("상세") {
    coordinator.show(.detail(id: item.id))
}
```

- **기계 대조(부분)**: SwiftLint `custom_rules`로 View 파일(`*View.swift`)에서 `pushViewController`·`present(` 호출을 금지할 수 있다. (가정: 커스텀 룰 등록 여부는 프로젝트별. 의미 판단은 리뷰 보완.)

## 의존 방향: View → Coordinator (단방향)

`View`/`ViewModel`은 Coordinator를 의존(주입받아 호출)할 수 있지만, **Coordinator는 구체 `View` 타입을 의존하지 않는다**. Coordinator는 "목적지(Route)"라는 추상만 다루고, 그 Route를 실제 `View`로 만드는 책임은 한 곳(팩토리/빌더)에 둔다. Coordinator가 화면마다 구체 `View`를 `import`하면 화면이 늘 때마다 Coordinator가 비대해지고, 모듈 분리 시 역방향 의존이 생긴다.

전환 목적지는 enum(`Route`/`Destination`)으로 타입화한다 — 문자열 식별자로 분기하지 않는다.

## 딥링크는 URL → Route로 번역 후 같은 경로로 흘린다

딥링크/유니버설 링크는 별도의 전환 경로를 만들지 않는다. URL을 `Route`로 **번역**한 뒤, 일반 전환과 동일한 Coordinator 경로로 흘린다. 그래야 "딥링크로 중간 화면에 바로 진입" 같은 케이스에서 네비게이션 스택이 일반 진입과 동일하게 복원된다.

- URL 파싱(스킴·경로·쿼리 → `Route`)은 한 곳에 모은다. 화면마다 흩지 않는다.
- 콜드 스타트(앱이 꺼진 상태 진입)와 웜 스타트(실행 중 진입)를 모두 처리한다 — 콜드 스타트는 초기 Route로, 웜 스타트는 현재 스택 위 전환으로.
