# Clean Architecture 레이어 경계 규칙

레이어 간 import·의존 방향을 기계 대조 가능한 "~해라/~금지" 규칙으로 둔다. DIP·단방향·Anti-Corruption의 판단 근거·트레이드오프는 [principles/personal/architecture/clean-architecture.md](../../../principles/personal/architecture/clean-architecture.md)가 담당하고, 이 문서는 규칙만 둔다.

프로젝트에 `.claude/docs/clean-architecture.md`가 있으면 **그 문서가 레이어·경계의 1차 출처**다. 레이어 목록·의존 허용표·세부 경계가 이 문서와 어긋나면 프로젝트 문서를 따른다. 이 문서는 프로젝트 문서가 없거나 침묵하는 부분을 메우는 방법론으로 읽는다.

## 의존은 바깥→안쪽 한 방향이다

레이어 의존은 안쪽(도메인)을 향하는 단방향이다. 안쪽 레이어는 바깥 레이어를 모른다.

```
Feature ──→ Domain ←── Data
            │
            ▼
           Core   (Networking·DesignSystem도 Core를 의존)
```

- **역방향 금지**: Domain이 Feature/Data를, Core가 자신을 의존하는 어떤 레이어를 의존하지 않는다.
- **수평 금지**: Feature 모듈이 다른 Feature 모듈을 직접 의존하지 않는다. 공유가 필요하면 그 부분을 Domain/Core로 내린다.
- **사이클 금지**: 의존이 자기 자신으로 돌아오는 경로를 만들지 않는다.

## Feature는 비즈니스 로직을 직접 구현하지 않는다

Feature(`<도메인>ViewController` 등)는 도메인 규칙·데이터 접근을 직접 짜지 않고 **UseCase protocol을 통해서만** 호출한다. ViewController는 주입받은 UseCase의 `execute`를 부르고 결과를 화면에 반영할 뿐이다.

```swift
// ❌ bad — ViewController가 Repository를 직접 잡고 규칙을 구현
final class ProfileViewController: UIViewController {
    let repository: ProfileRepository
    func load() {
        let profile = repository.fetch(id: userID)
        guard profile.isActive, profile.points >= threshold else { return } // 도메인 규칙이 화면에 샘
    }
}

// ✅ good — UseCase protocol 뒤에 규칙을 두고 호출만 한다
final class ProfileViewController: UIViewController {
    let loadProfileUseCase: LoadProfileUseCase
    func load() {
        let profile = try await loadProfileUseCase.execute(id: userID)
    }
}
```

- UseCase는 protocol + `Default<...>` 구현 쌍으로 두고, Feature는 protocol에만 의존한다(구체 구현 import 금지).
- 반대로 **UseCase는 UI 관심사를 모른다** — UseCase·Domain 타입에 화면 상태·포맷팅·표시 문자열을 넣지 않는다.

## Domain은 바깥 레이어를 import하지 않는다

Domain(Entity·ValueObject·UseCase protocol·Repository protocol)은 UI·인프라를 모른다.

- **금지 import**: Domain에서 `UIKit`, `SwiftUI`, `Networking`(또는 그 안의 `URLSession`·HTTP 타입), Data 레이어 타입.
- Entity는 `Codable`을 직접 준수하지 않는다(직렬화는 인프라 관심사 → Data의 DTO 책임).
- **기계 대조**: Domain 패키지 소스에서 `import UIKit`/`import SwiftUI`/`import Networking` grep → 0건이어야 한다.

```bash
grep -rn "import \(UIKit\|SwiftUI\|Networking\)" Sources/Domain
```

## Data와 Feature는 서로를 모른다

Data와 Feature는 직접 의존하지 않는다. 둘은 Domain의 추상(Repository protocol·UseCase protocol)을 통해서만 연결되고, 구체 구현을 묶는 일은 컴포지션 루트(`AppDependencies`)가 App 레이어에서 한다.

- Feature는 `<...>Impl`(Data의 Repository 구현)을 import하지 않는다 — `<Entity>Repository` protocol(Domain)에만 의존한다.
- Data는 ViewController·화면 타입을 import하지 않는다.
- 구체 구현(`*Impl`·`Default*`)을 끼워 넣는 것은 `AppDependencies` 한 곳뿐이다. App 외의 레이어는 구체 구현을 import하지 않고, 의존은 생성자 주입으로만 받는다.

## DesignSystem은 Feature가 의존하는 안쪽 레이어다

DesignSystem(디자인 토큰·공용 UI 컴포넌트)은 Core만 의존하는 안쪽 레이어이고, Feature가 그것을 의존한다(Feature → DesignSystem). 역방향(DesignSystem이 Feature를 의존)은 금지다.

- Feature는 DesignSystem이 노출한 토큰·컴포넌트를 import해 쓴다. DesignSystem은 특정 화면(Feature)을 알지 못한다.
- 한 도메인에서만 쓰는 컴포넌트를 DesignSystem으로 끌어올리지 않는다 — 그 도메인의 Feature에 둔다.

## DTO는 Data 내부에 가둔다

`<Entity>DTO`는 Data 레이어 `internal` 타입이다. Domain·Feature에 노출하지 않는다.

- DTO ↔ Entity 매핑은 Data 안에서 끝낸다. Domain·Feature는 항상 Entity만 본다.
- **기계 대조**: DTO 타입을 `public`으로 노출하지 않았는지, Domain/Feature 소스에서 `DTO` 참조가 없는지 grep으로 확인한다.

## 인프라 오류는 Data에서 DomainError로 번역한다

`NetworkError`·`DecodingError` 같은 인프라 오류는 Data 경계를 넘지 못한다. Repository 구현이 이를 잡아 **`DomainError`로 번역**해 던진다. Domain·Feature는 `NetworkError`를 보지 못한다.

```swift
// ✅ good — Data의 Repository 구현이 경계에서 번역
final class ProfileRepositoryImpl: ProfileRepository {
    func fetch(id: ProfileID) async throws -> Profile {
        do {
            let dto: ProfileDTO = try await client.request(...)
            return dto.toDomain()
        } catch let error as NetworkError {
            throw DomainError.from(error) // 인프라 오류를 도메인 언어로
        }
    }
}
```

- **기계 대조**: Domain/Feature 소스에서 `NetworkError`·`DecodingError` 참조 grep → 0건이어야 한다.

## 검증: Package.swift dependencies 대조

레이어 단방향은 빌드가 아니라 **각 패키지의 `Package.swift` `dependencies` 배열을 grep으로 대조**해 강제한다(`tuist graph`는 사용하지 않는다). 위 「의존은 바깥→안쪽」의 방향 규칙을 어긴 선언을 잡는다.

- 각 `Package.swift`의 `.target(... dependencies: [...])`에 **실제 import하는 레이어만** 선언한다. 빌드를 통과시키려 임시로 의존을 추가하지 않는다.
- 방향 규칙을 어기는 선언(예: Domain target의 dependencies에 `Networking` 또는 Feature 패키지가 등장)이 있는지 grep으로 점검한다.
