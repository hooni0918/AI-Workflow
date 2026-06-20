# 수정하기 쉬운 SwiftUI 코드 (예시)

> **예시 (참고용).** SwiftUI를 쓰는 프로젝트의 예시다. 마스터 표준이 아니며, 네 프로젝트의 `.claude/docs`에 네 것으로 정의해 대체하라.


응집도가 높고 결합도가 낮은 코드를 지향한다. 리뷰 피드백은 응집도·결합도의 **종류**를 짚어 근거를 댄다.

## 응집도 — 한 단위가 한 관심사만

한 `View`나 ViewModel이 여러 관심사를 동시에 담당하면 응집도가 낮은 신호다. 화면(`View`)에 서로 다른 관심사의 상태·부수효과가 쌓이면, "같은 화면에 있다"는 이유만으로 묶인 우연적(coincidental) 응집이다. 관심사별로 분리한다.

```swift
// ❌ bad — 한 화면에 검색어 동기화 · 데이터 로딩 · 분석 이벤트가 섞임
struct ProductListScreen: View {
    @State private var keyword = ""
    @State private var products: [Product] = []
    @State private var isLoading = false

    var body: some View {
        ProductList(products: products, isLoading: isLoading)
            .searchable(text: $keyword)
            .onChange(of: keyword) { _, new in
                analytics.track("product_list_search", ["keyword": new])
                isLoading = true
                Task {
                    products = await api.fetchProducts(matching: new)
                    isLoading = false
                }
            }
    }
}

// ✅ good — 데이터·로딩은 ViewModel이, 분석은 별도 책임으로 분리
struct ProductListScreen: View {
    @State private var viewModel: ProductListViewModel

    var body: some View {
        ProductList(products: viewModel.products, isLoading: viewModel.isLoading)
            .searchable(text: $viewModel.keyword)
            .task(id: viewModel.keyword) { await viewModel.reload() }
    }
}
```

화면은 "무엇을 그리는가"만, 상태·로딩·페칭은 ViewModel이, 분석 같은 부가 관심사는 또 다른 단위가 맡는다.

## 결합도 — 단위 사이의 연결을 약하게

- **전역 가변 상태 공유(common coupling) 회피**: 여러 화면이 하나의 가변 싱글턴 상태를 직접 읽고 쓰면, 한 화면의 변경이 다른 화면의 동작을 예고 없이 바꾼다. 의존을 주입으로 명시하고, 공유 상태는 경계(저장소·환경 값)를 두고 다룬다.
- **내부 구현 접근(content coupling) 회피**: 자식 `View`가 부모의 상태 객체 전체를 받아 그 내부 프로퍼티를 직접 만지면, 부모 구조가 바뀔 때 자식도 깨진다. 자식은 자기에게 필요한 값과 콜백만 받는다(swiftui-basics.md 「@State / @Binding」).

## 미구현·미연결은 컴파일러가 다 잡지 못한다

상태 객체를 stub으로 세우고 나중에 채우는 경우, 빈 본문·미초기화 프로퍼티는 컴파일러가 강제로 드러내지 못한다. 이 한계의 정확한 범위와 무엇을 테스트·리뷰가 맡아야 하는지는 [testing-strategy/assumptions.md](../../testing-strategy/assumptions.md) 「stub 검증의 한계」가 단일 출처다.
