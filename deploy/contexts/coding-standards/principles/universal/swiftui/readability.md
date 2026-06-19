# 읽기 쉬운 SwiftUI 코드

> **현재 미채택** — MINO의 UI는 UIKit 단독이라 SwiftUI를 쓰지 않는다. 아래는 향후 SwiftUI 도입 시에만 적용한다.

## 원칙: 이해에 필요한 사전지식이 적은 코드

기획·디자인·동작을 알아야 하는 것은 괜찮다. 하지만 코드가 그것과 1대1로 매칭되지 않아 **내부 구현의 사전지식을 많이 요구할수록** 읽기 어려운 코드다. 이름·입력·출력만으로 동작을 유추할 수 있으면 읽기 쉽다.

## 탑다운 스캔 테스트

`View`의 `body`나 ViewModel을 위에서 아래로 이름만 훑으며 내려갈 때, 이해가 안 되는 구간이 생기면 안 된다. 내부 구현을 열어보지 않아도 흐름이 유추되어야 한다.

```swift
struct OrderScreen: View {
    @State private var viewModel: OrderViewModel

    var body: some View {
        ScreenLayout {
            CartSummarySection(items: viewModel.items, total: viewModel.total)
            OrderButton(isLoading: viewModel.isSubmitting) {
                viewModel.submit()
            }
        }
        .task { await viewModel.loadCart() }
    }
}
```

위에서 아래로 이름만 읽으면: 장바구니 요약을 보여주고 → 주문 버튼을 두고 → 진입 시 장바구니를 불러온다. 내부 구현을 몰라도 역할이 드러난다.

## 인지부하 낮추기 — 조건을 이름에 담는다

`body`의 분기 조건이나 modifier 인자가 길거나 직관적이지 않으면, 의미 있는 이름의 computed property로 빼서 거기에 담는다.

```swift
// ❌ bad — 조건식이 body 안에 그대로 노출
if user.subscription != nil && user.subscription!.expiresAt > .now && !user.isTrial {
    PremiumBadge()
}

// ✅ good — 의미 있는 이름으로 분리 (강제 언래핑도 제거됨)
private var showsPremiumBadge: Bool {
    guard let subscription = user.subscription, !user.isTrial else { return false }
    return subscription.expiresAt > .now
}

// body 안에서는
if showsPremiumBadge {
    PremiumBadge()
}
```

조건을 이름으로 빼면 `body`가 "무엇을 그리는가"만 읽히고, "언제 그리는가"의 판단은 이름이 설명한다.

## 추출이 아니라 추상화

`body`가 길다고 기계적으로 잘라 하위 `View`로 빼면, 부모와 자식이 같은 상태를 잘게 나눠 들고 있어 오히려 추적이 어려워진다. 자른 단위가 **하나의 의미(한 구역, 한 책임)**를 이루는지 본다. 의미 단위가 아니면 자르지 말고, 자를 거면 그 단위가 독립된 입력만으로 그려지도록 추상화한다(rules/universal/swiftui/basics.md 「View 분리 기준」).
