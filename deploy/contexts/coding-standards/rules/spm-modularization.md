# SPM 모듈화 규칙

SPM 로컬 패키지로 모듈을 나눌 때의 범용 컨벤션이다 — `Package.swift`를 어떻게 적고, 의존 방향을 무엇으로 검증하는가. 이 문서는 특정 아키텍처·레이어 목록을 고르지 않는다.

**레이어 목록·허용 의존 방향 자체는 마스터가 정의하지 않는다.** 그 정의는 사용 레포가 공급한다 — 프로젝트의 `.claude/docs/architecture.md`(서술)와 `layer-rules.json`(기계 대조용 허용표). 둘 중 하나라도 있으면 그것을 **1차 출처**로 따르고, 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행한다. (구체 레이어를 어떻게 적는지의 예시는 [examples/clean-architecture-layer-rules.md](../examples/clean-architecture-layer-rules.md).)

이 문서는 그 레이어 정의를 SPM manifest로 어떻게 옮기고, 옮긴 결과를 어떻게 검증하는가에 집중한다.

## 레이어 경계: SPM 로컬 패키지 계층

모듈을 레이어로 가르고, 의존은 **허용된 방향 한 쪽**으로만 흐른다. 레이어가 무엇이고 어느 방향이 허용되는지는 위 프로젝트 출처(`architecture.md`·`layer-rules.json`)가 정의한다. 방향 규칙의 공통 골격은 다음 세 가지다.

- **역방향 금지**: 허용 방향의 반대로 의존하지 않는다.
- **수평 금지**: 같은 레이어 모듈끼리 직접 의존하지 않는다. 공유가 필요하면 그 부분을 더 하위(공통) 레이어로 내린다.
- **사이클 금지**: 어떤 경로로도 의존이 자기 자신으로 돌아오지 않는다.

레이어 수·이름은 레포마다 다르다. 실제 레포 레이어는 패키지 디렉토리 구성과 각 `Package.swift`의 `dependencies` 배열로 확인하고, 프로젝트 `layer-rules.json`/`architecture.md`를 1차 출처로 본다.

## 도메인 종속 코드의 배치

특정 도메인에서만 쓰는 타입·유틸·컴포넌트는 공통(하위) 레이어가 아니라 **그 도메인의 모듈**에 둔다.

- **❌ bad**: 한 도메인에서만 쓰는 컴포넌트를 공통 UI/기반 레이어에 생성
- **✅ good**: 그 도메인의 모듈 안에 생성

공통 레이어에는 **둘 이상의 도메인**이 함께 쓰는 것만 둔다. "언젠가 재사용할지 모른다"는 이유로 하위 레이어에 올리지 않는다 — 끌어올린 순간 그 도메인을 떼어낼 수 없게 묶이고, 하위로 잘못 내린 것은 의존자가 생긴 뒤 되돌리기 비싸다.

## 경계 타입은 하위 레이어에 둔다

두 모듈이 주고받는 경계 타입(엔티티, 추상 인터페이스)은 의존 방향상 **하위(공통) 레이어**에 둔다. 상위가 정의한 타입을 하위가 의존하면 역방향이다.

- 인터페이스(protocol)는 하위 레이어에, 그 구현은 상위 레이어에 두고, 소비자는 하위의 인터페이스에만 의존한다.
- 인프라 포맷 타입(DTO 등)은 인프라 모듈 internal로 가둔다. 상위 레이어로 노출하지 않는다 — 상위로 흘리면 경계가 인프라 포맷에 묶인다.

구체 레이어 이름·접미사로 이 규칙을 어떻게 적는지는 프로젝트 `.claude/docs`가 정의한다(예시는 위 examples 참고).

## Package.swift 컨벤션

- 모듈 하나당 manifest의 `dependencies`에 **실제로 import하는 모듈만** 선언한다. 빌드를 통과시키려고 임시로 역방향·수평 의존을 추가하지 않는다 — 미선언 import는 SPM 컴파일이 잡지만, 선언된 역방향 의존은 빌드가 아니라 그래프 대조가 잡는다(아래 「검증」).
- 로컬 패키지 의존은 `.package(path: "../X")`로 선언한다. `target`의 `dependencies`에는 해당 패키지가 노출한 라이브러리 product를 적는다.
- product는 `.library(name:targets:)`, 소스 타깃은 `.target(name:dependencies:)`, 테스트 타깃은 `.testTarget(name:dependencies:)`로 같은 패턴을 유지한다. 테스트 타깃 이름은 `<모듈>Tests`.
- 공통 빌드 설정(`swift-tools-version`, `platforms`, 각 타깃의 `swiftLanguageModes`)은 **형제 패키지와 동일한 값**으로 둔다. 모듈마다 복붙하되 값을 갈라지게 두지 않는다. 구체 버전 값은 프로젝트 기존 패키지에 맞추고, 기준이 없으면 사용자에게 확인한다.
- 모듈 디렉토리·product·타깃 이름을 레이어와 일치시킨다. 이름만으로 레이어를 식별할 수 있어야 그래프 위반을 사람이 읽어낼 수 있다.

```swift
// swift-tools-version: <형제 패키지와 동일>
import PackageDescription

let package = Package(
    name: "<모듈>",
    platforms: [/* 형제 패키지와 동일 */],
    products: [
        .library(name: "<모듈>", targets: ["<모듈>"]),
    ],
    dependencies: [
        .package(path: "../../<하위레이어>/<모듈>"),
        // dependencies에는 실제 import하는 모듈만. 역방향·수평 금지.
    ],
    targets: [
        .target(
            name: "<모듈>",
            dependencies: ["<의존모듈>"],
            swiftSettings: [/* 형제 패키지와 동일한 swiftLanguageMode */]
        ),
        .testTarget(
            name: "<모듈>Tests",
            dependencies: ["<모듈>"],
            swiftSettings: [/* 형제 패키지와 동일한 swiftLanguageMode */]
        ),
    ]
)
```

## App 타깃 링크

App(컴포지션 루트)은 manifest 생성 도구로 자동 생성하지 않는다. App의 `.xcodeproj`에 로컬 패키지를 **수동으로 링크**한다.

- 새 모듈을 App이 직접 쓰면 App `.xcodeproj`의 패키지 의존에 그 product를 추가한다. App은 보통 모든 레이어를 의존할 수 있는 유일한 레이어다(프로젝트 출처가 다르게 정의하면 그것을 따른다).
- 컴포지션 루트만 구체 구현을 import해 조립한다. App 외의 모듈은 구체 구현을 import하지 않고, 의존은 생성자 주입으로 받는다.

## 검증

방향 규칙은 모두 `dependencies`에 선언하면 컴파일을 통과하므로, 빌드 성공을 의존 검증의 근거로 쓰지 않는다. 그래프 생성 도구(`tuist graph` 등)에 의존하지 않는다. 대신 잡는 대상이 겹치지 않는 두 검사를 **분리**해 둘 다 돌린다.

- **미선언 import**: `xcodebuild`로 잡는다. `dependencies`에 없는 모듈을 import하면 SPM이 컴파일 실패로 강제하므로, 빌드 성공이 곧 "모든 import가 선언됨"의 증거다.
- **레이어 방향(역방향·수평·사이클)**: `check_spm_layers.py`로 각 `Package.swift`의 `dependencies`를 추출해 프로젝트 허용표와 대조한다. 선언된 역방향은 빌드가 못 잡으므로 이 대조가 유일한 게이트다.

```bash
python3 check_spm_layers.py <packages_dir> --rules <프로젝트 layer-rules.json>
```

`--rules`에는 프로젝트가 공급한 `layer-rules.json`(키=모듈, 값=그 모듈이 의존해도 되는 하위 모듈 목록)을 넘긴다. 이 파일이 없으면 프로젝트 `architecture.md`의 허용표를 옮겨 만들거나 사용자에게 확인한다 — 마스터가 임의의 레이어 목록을 채워 넣지 않는다.

두 검사가 잡는 대상이 겹치지 않으므로 둘 다 실행하고, 결과를 분리해서 보고한다. 운용 절차·판정 기준의 단일 출처는 [spm-module 스킬](../../../skills/spm-module/SKILL.md)이고, 빌드·검사 명령의 전제는 [testing-strategy/assumptions.md](../../testing-strategy/assumptions.md)다.
