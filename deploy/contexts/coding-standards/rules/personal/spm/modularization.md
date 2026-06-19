# SPM 모듈화 규칙

SPM 로컬 패키지로 모듈을 나눌 때의 경계·의존 방향 규칙과 `Package.swift` 컨벤션이다. 의존 그래프를 실제로 검증하는 도구·절차(`Package.swift`의 `dependencies` 배열 대조 + `xcodebuild`)는 [spm-module 스킬](../../../../../skills/spm-module/SKILL.md)이 단일 출처이고, 빌드·검사 명령 전제는 [testing-strategy/assumptions.md](../../../../testing-strategy/assumptions.md)가 단일 출처다. 이 문서는 "어느 방향이 맞는가"의 규칙과 manifest를 어떻게 적는가만 정의한다.

레이어 목록·허용 경계 자체는 [clean-architecture/layer-rules.md](../clean-architecture/layer-rules.md)가 출처이며, 그 출처는 **프로젝트에 `.claude/docs/clean-architecture.md`가 있으면 그 문서를 1차 출처(single source)로 따른다**. 이 문서는 그 레이어 정의를 SPM manifest로 어떻게 옮기는가에 집중한다.

## 레이어 경계: SPM 로컬 패키지 계층

모듈을 Clean Architecture 레이어로 가른다. 의존은 **위(상위)에서 아래(하위) 한 방향**이다. 레이어의 책임과 허용 의존은 위 레이어 출처를 따른다.

| 레이어 | 담는 것 | 의존 가능 대상 |
|---|---|---|
| **App** | 컴포지션 루트, DI 조립, 앱 진입·구성 | 전부 |
| **Feature** | 화면·사용자 흐름 (UIKit VC가 UseCase 직접 호출) | Domain, DesignSystem |
| **Data** | Repository 구현·DTO·인프라 연동·오류 번역 | Domain, Networking |
| **DesignSystem** | 디자인 토큰·공용 UI 컴포넌트 | Core |
| **Domain** | 엔티티·ValueObject·UseCase·Repository 인터페이스 | Core |
| **Networking** | 네트워크 전송·세션·요청 추상 | Core |
| **Core** | 레이어 무관 공용 기반 (확장·로깅·유틸) | (없음 — 최하위) |

- **역방향 금지**: 하위가 상위를 의존하지 않는다. Domain → Feature, Core → Domain 같은 edge는 모두 금지.
- **수평 금지**: 같은 레이어 모듈끼리 직접 의존하지 않는다. `Feature ↛ Feature`. 공유가 필요하면 그 부분을 하위 레이어로 내린다.
- **사이클 금지**: 어떤 경로로도 의존이 자기 자신으로 돌아오지 않는다.

```
App ──→ (전부)
Feature ──→ Domain, DesignSystem
Data ──→ Domain, Networking
DesignSystem, Domain, Networking ──→ Core
Core ──→ (없음)
```

레이어 수·이름은 레포마다 다를 수 있다. 실제 레포 레이어는 `Packages/` 디렉토리 구성과 각 `Package.swift`의 `dependencies` 배열로 확인하고, 프로젝트 `.claude/docs/clean-architecture.md`가 있으면 그것을 1차 출처로 본다.

## 도메인 종속 코드의 배치

특정 도메인에서만 쓰는 타입·유틸·컴포넌트는 `Core`가 아니라 **그 도메인의 Feature/Domain 모듈**에 둔다.

- **❌ bad**: Profile에서만 쓰는 `ProfileBadgeView`를 `DesignSystem`에 생성
- **✅ good**: `Feature/Profile` 안에 생성

`Core`·`DesignSystem`에는 **둘 이상의 도메인**이 공통으로 쓰는 것만 둔다. "언젠가 재사용할지 모른다"는 이유로 하위 레이어에 올리지 않는다 — 끌어올린 순간 그 도메인을 떼어낼 수 없게 묶이고, 하위로 잘못 내린 것은 의존자가 생긴 뒤 되돌리기 비싸다.

## 경계 타입은 하위 레이어에 둔다

두 모듈이 주고받는 경계 타입(엔티티, Repository protocol)은 의존 방향상 **하위 레이어**에 둔다. 상위가 정의한 타입을 하위가 의존하면 역방향이다.

- Repository는 protocol을 Domain에, `*Impl` 구현을 Data에 둔다. Feature는 Domain의 protocol에만 의존한다.
- DTO는 Data internal로 가둔다. Domain·Feature로 노출하지 않는다 — DTO를 상위로 흘리면 경계가 인프라 포맷에 묶인다.

## Package.swift 컨벤션

- 모듈 하나당 manifest의 `dependencies`에 **실제로 import하는 모듈만** 선언한다. 빌드를 통과시키려고 임시로 역방향·수평 의존을 추가하지 않는다 — 미선언 import는 SPM 컴파일이 잡지만, 선언된 역방향 의존은 빌드가 아니라 그래프 대조가 잡는다(전제·도구는 위 cross-ref 참조).
- 로컬 패키지 의존은 `.package(path: "../X")`로 선언한다. `target`의 `dependencies`에는 해당 패키지가 노출한 라이브러리 product를 적는다.
- product는 `.library(name:targets:)`, 소스 타깃은 `.target(name:dependencies:)`, 테스트 타깃은 `.testTarget(name:dependencies:)`로 같은 패턴을 유지한다. 테스트 타깃 이름은 `<모듈>Tests`.
- 공통 빌드 설정은 모든 패키지에서 동일하게 둔다: `swift-tools-version: 6.0`, `platforms: [.iOS(.v17)]`, 각 타깃에 `swiftLanguageModes: [.v6]`. 모듈마다 복붙하되 값을 갈라지게 두지 않는다.
- 모듈 디렉토리·product·타깃 이름을 레이어와 일치시킨다(`Packages/<레이어>/<모듈>`). 이름만으로 레이어를 식별할 수 있어야 그래프 위반을 사람이 읽어낼 수 있다.

```swift
// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Profile",
    platforms: [.iOS(.v17)],
    products: [
        .library(name: "Profile", targets: ["Profile"]),
    ],
    dependencies: [
        .package(path: "../../Domain/Domain"),
        .package(path: "../../DesignSystem/DesignSystem"),
        // dependencies에는 실제 import하는 모듈만. 역방향·수평 금지.
    ],
    targets: [
        .target(
            name: "Profile",
            dependencies: ["Domain", "DesignSystem"],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
        .testTarget(
            name: "ProfileTests",
            dependencies: ["Profile"],
            swiftSettings: [.swiftLanguageMode(.v6)]
        ),
    ]
)
```

## App 타깃 링크

App은 `project.yml`(XcodeGen)이나 Tuist manifest로 생성하지 않는다. `App.xcodeproj`에 로컬 패키지를 **수동으로 링크**한다.

- 새 모듈을 App이 직접 쓰면 `App.xcodeproj`의 패키지 의존에 그 product를 추가한다. App은 모든 레이어를 의존할 수 있는 유일한 레이어다.
- 컴포지션 루트(`AppDependencies`)만 구체 구현(`*Impl`·`Default*`)을 import해 조립한다. App 외의 모듈은 구체 구현을 import하지 않는다.

## 검증

방향 규칙은 모두 `dependencies`에 선언하면 컴파일을 통과하므로, 빌드 성공을 의존 검증의 근거로 쓰지 않는다. `tuist inspect`/`tuist graph` 같은 그래프 도구는 쓰지 않는다(Tuist 미사용). 대신 두 검사를 **분리**해 돌린다.

- **미선언 import**: `xcodebuild build`로 잡는다. `dependencies`에 없는 모듈을 import하면 SPM이 컴파일 실패로 강제하므로, 빌드 성공이 곧 "모든 import가 선언됨"의 증거다.
- **레이어 방향(역방향·수평·사이클)**: 각 `Package.swift`의 `dependencies` 배열(`.package(path:)`)을 grep으로 추출해 위 「레이어 경계」 규칙과 대조한다. 선언된 역방향은 빌드가 못 잡으므로 이 대조가 유일한 게이트다.

두 검사가 잡는 대상이 겹치지 않으므로 둘 다 실행한다. 운용 절차·판정 기준의 단일 출처는 위 [spm-module 스킬](../../../../../skills/spm-module/SKILL.md)이다.
