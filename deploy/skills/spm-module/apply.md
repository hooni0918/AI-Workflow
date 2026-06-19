# APPLY — 생성 + 빌드 + 검증 2-track

SKILL.md 「작업 진행 순서」의 APPLY 세션 본문이다. PLAN의 설계서·manifest 변경안을 적용 지시서로 받아 파일을 만들고 빌드한 뒤, 빌드와 **독립된** 두 검사로 레이어 규칙 준수를 증명한다.

진입 시 SKILL.md 「[CRITICAL] 지킬 원칙」, [conventions/module-layers.md](conventions/module-layers.md), [conventions/deps-verify.md](conventions/deps-verify.md)를 먼저 읽는다. 대상 프로젝트에 `.claude/docs/clean-architecture.md`가 있으면 레이어 목록·경계의 **1차 출처**로 보고 그것을 따른다 (이 스킬은 방법론, 프로젝트 사실은 거기에 위임).

## 0. 입력 확인

PLAN 산출물(레이어 설계서·manifest 변경안)을 읽는다. 없으면 진행하지 않고 사용자에게 PLAN 선행을 안내한다 — 검증 기준이 없는 채로 적용하면 "무엇을 어겼는지" 판정할 근거가 없다.

- 설계서를 **적용 지시·인덱스**로 읽는다. 검증 기준으로 읽지 않는다 (SKILL.md 「검증 기준 = 진실 원천」).
- 현재 의존을 다시 확인한다: 각 `Package.swift`의 `dependencies` 배열과 App 타깃 링크를 grep으로 재확인 (PLAN이 본 "before"와 달라졌을 수 있으므로 재확인).

## 1. manifest 반영

PLAN의 manifest 변경안을 실제 `Package.swift`에 반영한다.

- 변경안 diff 그대로 적용한다. APPLY가 임의로 의존을 추가·삭제하지 않는다 — 그래프는 PLAN이 설계한 것이다. 적용 중 PLAN 설계가 빌드 불가임이 드러나면(예: 누락된 하위 모듈) 임의 보정하지 말고 사용자에게 보고한다 (「입력 산출물 비판적 검토」에 준해 결정 위임 형태로).
- 새 패키지면 `Package.swift`를 형제 패키지와 **동일 패턴**으로 만든다: product는 `.library(name:"<M>",targets:["<M>"])` 단일, target은 `.target(name:"<M>")` + `.testTarget(name:"<M>Tests")`, product·target 이름은 패키지명과 일치, swift-tools 6.0 / platforms `[.iOS(.v17)]` / swiftLanguageModes `[.v6]`. 의존은 `.package(path:"../X")` 로컬 경로로 적는다.

## 2. 패키지 디렉토리·소스 스켈레톤 생성

`Packages/<New>/` 아래에 디렉토리와 최소 소스를 만든다.

- 구조는 형제 패키지를 미러링한다: `Package.swift` + `Sources/<M>/` + `Tests/<M>Tests/`.
- 공개 타입은 **stub**으로 만든다. stub 규칙은 SKILL.md 「stub은 시그니처 정합만 보증한다」를 따른다:
  - 공개 시그니처는 의존 모듈이 컴파일되도록 갖춘다 (DDD 계층이면 Repository/UseCase protocol·DomainError 등 공개 경계 타입의 시그니처).
  - **빈 함수 본체는 컴파일러가 미구현을 못 잡는다** — 본체 미구현 항목을 종료 보고에 명시한다.
  - **저장 프로퍼티 초기값은 `fatalError`로 못 메운다.** 저장 상태가 있는 타입은 더미 초기값을 박거나 본체 구현으로 미룬다.
  - strict concurrency(SWIFT_STRICT_CONCURRENCY=complete)가 강제이므로 stub의 공개 타입도 동시성 경계(`Sendable`·actor isolation)를 시그니처에 맞춰 둔다. UIKit 단독이라 `@Observable`은 쓰지 않는다.

## 3. App.xcodeproj 링크 (수동 pbxproj 편집)

새 패키지를 App이 쓰려면 App.xcodeproj에 로컬 패키지를 등록한다. `project.yml`이 없으므로 **pbxproj를 수동 편집**한다 (생성기로 재생성하지 않는다).

- **PBXFileReference (folder)**: `Packages/<New>/`를 로컬 패키지 폴더 참조로 추가하고, App의 그룹 트리에 넣는다.
- **XCSwiftPackageProductDependency**: 패키지 product `<M>`에 대한 product 의존을 추가한다.
- **타깃 link**: App 타깃의 `packageProductDependencies`(및 Frameworks 빌드 페이즈)에 위 product를 연결한다.
- 형제 패키지가 이미 같은 방식으로 링크돼 있으므로, 그 항목을 grep으로 떠서 동일 형식을 미러링한다. UUID·참조 형식이 어긋나면 프로젝트가 열리지 않거나 링크가 누락되므로, 추가 후 4단계 빌드로 링크 성립을 확인한다.

## 4. 빌드

```bash
xcodebuild build -project App/App.xcodeproj -scheme App -destination 'generic/platform=iOS Simulator'
```

- 정답 빌드 명령은 위 한 줄이다 (실측 BUILD SUCCEEDED 게이트). 빌드 통과 = "선언된 의존 안에서 타입이 맞고 링크가 성립한다".
- 빌드 실패 시 원인을 분류한다:
  - **시그니처 불일치**: stub 시그니처가 의존자 기대와 안 맞음 → stub 시그니처 수정.
  - **미선언 import**: 소스가 import 하나 `Package.swift` `dependencies`에 없음 → SPM이 컴파일 실패로 잡는다. PLAN 설계 의존 범위 안에서 manifest를 교정하거나(설계 내), 설계 위반이면 사용자 보고.
  - **링크 누락**: App에서 새 모듈을 못 찾음 → 3단계 pbxproj 등록 점검.
- 빌드 통과를 레이어 검증 통과로 보고하지 않는다 (SKILL.md 「빌드 성공 ≠ 레이어 규칙 준수」). `dependencies`에 역방향을 적으면 컴파일은 통과하므로, 5단계 grep 대조가 별도로 필요하다.

## 5. 검증 track A — 미선언 import (컴파일)

[conventions/deps-verify.md](conventions/deps-verify.md)의 track A 절차를 따른다.

- 소스가 import 하지만 `Package.swift` `dependencies`에 **선언되지 않은 import**는 SPM이 컴파일 단계에서 실패로 잡는다 (manifest↔소스 정합). 즉 4단계 빌드 통과가 곧 track A 통과다.
- 단 이 검사는 **레이어 방향을 보지 않는다.** 방향 검증은 track B가 담당한다.

## 6. 검증 track B — 레이어 단방향 위상 (`dependencies` grep 대조)

[conventions/deps-verify.md](conventions/deps-verify.md)의 track B 절차를 따른다.

- 각 `Package.swift`의 `dependencies` 배열을 grep으로 떠서 [conventions/module-layers.md](conventions/module-layers.md)(또는 프로젝트 `.claude/docs/clean-architecture.md`)의 허용 방향과 대조한다.
- 점검: 역방향 의존 0건 / 수평(동일 레이어 직접) 의존 0건 / 사이클 0건.
- 위반이 있으면 `dependencies`·소스를 고치고 4단계부터 재실행한다. **위반을 "가정"으로 통과시키지 않는다** — 방향 위반은 사실 위반이다.
- 대조 기준은 실제 `dependencies` 배열과 conventions·프로젝트 규칙이다. PLAN 설계서를 기준으로 대조하지 않는다 (자기증명 차단). `dependencies`에 역방향을 적어도 빌드는 통과하므로 배열 자체의 grep 대조가 필요하다 — 이게 '빌드 성공 ≠ 레이어 규칙 준수'의 SPM판이다.

> track A와 B는 잡는 대상이 다르다 (정합 vs 방향). 둘 다 통과해야 레이어 검증 통과다. 하나만 확인하고 "검증 완료"라 보고하지 않는다.

## 7. (선택) 테스트

테스트 타깃이 있으면 패키지 종류에 맞춰 돌린다.

- Core·Domain: `(cd Packages/<P> && swift test)`.
- Networking·Data·DesignSystem·Feature: `(cd Packages/<P> && xcodebuild test -scheme <P> -destination 'platform=iOS Simulator,id=<UDID>')`. UDID는 `xcrun simctl list devices available`로 조회한다 (name 단독 지정은 동명 중복 위험).
- App 타깃엔 테스트 번들이 없다 (앱레벨 테스트 부재). 새 패키지의 `<M>Tests` 타깃은 위 패턴 중 패키지 종류에 맞는 쪽으로 돌린다.

## 8. 종료 보고

다음을 보고한다.

- 생성한 패키지·디렉토리, 반영한 `Package.swift` 변경, App.xcodeproj 수동 링크 항목(PBXFileReference·product 의존·타깃 link)
- 빌드 결과 (`xcodebuild build … -scheme App` 통과/실패)
- **검증 2-track 결과 분리 명시**: track A(컴파일, 미선언 import) 결과 / track B(`dependencies` grep 대조, 레이어 방향) 결과. 둘 다 통과해야 "레이어 검증 통과".
- **stub 한계 명시**: 시그니처·레이어만 보증, 빈 본체 미구현 목록. 저장 프로퍼티 더미 초기값을 박은 곳.
- 남은 "가정" 라벨 (확인 못 한 target·테스트·lint 게이트 등)
- 본체 구현은 이 스킬 범위 밖임을 안내한다.
