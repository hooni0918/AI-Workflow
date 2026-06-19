# 네이밍 컨벤션

Swift API Design Guidelines를 기준으로 한다. 핵심은 **사용처(call site)에서 문장처럼 읽히는가**다.

## 사용처에서 읽히게

메서드·파라미터 이름은 호출하는 쪽에서 영어 문장처럼 읽히도록 짓는다.

```swift
// ❌ bad — 호출부가 모호
list.insert(item, 3)
remove(at: x, false)

// ✅ good — 호출부가 문장처럼 읽힘
list.insert(item, at: 3)
employees.remove(at: index)
```

- 첫 인자가 전치사구의 일부면 인자 레이블을 전치사로 시작한다 (`at:`, `from:`, `with:`).
- 부수효과 유무로 동사형을 가른다: 부수효과 있는 동작은 명령형 동사(`sort()`, `append()`), 값을 돌려주는 비변형 동작은 `-ed`/`-ing` 명사형(`sorted()`, `sorting`).

## 약어로 줄이지 않는다

변수·파라미터·클로저 인자를 한 글자나 의미 없는 약어로 줄이지 않고 원래 단어를 쓴다. 클로저 인자도 마찬가지다.

```swift
// ❌ bad
items.map { e in e.name }
let uc = SignInUseCase()

// ✅ good
items.map { entity in entity.name }
let signInUseCase = DefaultSignInUseCase()
```

널리 굳은 약어(`url`, `id`, `dto`)는 예외다. 약어의 대소문자는 통일한다(`userID`가 한 곳, `userId`가 다른 곳에 섞이지 않게).

## 타입·프로토콜·파일

- 타입(`struct`/`class`/`enum`)은 UpperCamelCase, 프로퍼티·메서드·인자는 lowerCamelCase.
- 능력을 나타내는 프로토콜은 `-able`/`-ible`/`-ing`(`Equatable`, `ProgressReporting`), 역할·명사형 프로토콜은 명사(`Repository`, `UseCase`).
- 한 파일에 한 주(主) 타입을 두고 **파일명을 그 타입명과 일치**시킨다 (`SignInUseCase.swift` → `protocol SignInUseCase`). 보조 확장·작은 헬퍼는 같은 파일에 둘 수 있다.
- 한 타입에 붙는 확장만 모은 파일은 `Type+Extensions.swift`로 짓는다.

## 역할 접미사 (Clean Arch + DDD + UIKit)

역할이 드러나도록 접미사를 일관되게 붙인다. 아래는 대상 프로젝트의 실측 규칙이다. `<도메인>`·`<Entity>`·`<동사>`는 자리표시자이며, 실제 도메인 명사·동사로 채운다.

- **화면**: `<도메인>ViewController` (UIKit `UIViewController`, 코드 기반 `NSLayoutConstraint` AutoLayout).
- **UseCase**: `<동사>UseCase`(protocol) + `Default<동사>UseCase`(구현)의 쌍. 단일 진입 메서드는 `execute`로 통일한다. UI 관심사를 두지 않는다.
- **Repository**: `<Entity>Repository`(protocol, Domain 레이어) + `<Entity>RepositoryImpl`(구현, Data 레이어, `final class`).
- **DTO**: `<Entity>DTO` (Data 레이어 `internal`, Domain에 노출 금지).
- **Entity / ValueObject**: Entity는 도메인 명사 그대로(`struct`), 식별자 VO는 `<Entity>ID`.
- **에러**: 도메인 오류는 `DomainError`, 인프라 오류는 `NetworkError`. 인프라 오류는 Data 레이어에서 `DomainError`로 번역한다(Domain은 `NetworkError`를 보지 못한다).
- **DesignSystem 토큰**: `App` 접두 enum(`AppColors`, `AppTypography`). 컴포넌트는 역할명(`TitleLabel`).

> 레이어별 import·경계, DTO 노출 금지, Anti-Corruption 같은 **경계 규칙의 1차 출처**는 대상 프로젝트의 `.claude/docs/clean-architecture.md`다. 그 파일이 있으면 그것을 따른다. 여기서는 네이밍 형태만 정의한다. 모듈 분리·레이어 import 규칙은 [모듈화](spm/modularization.md)·[레이어 규칙](clean-architecture/layer-rules.md) 참조.

## 기계 대조

- 케이스·길이 규칙(`type_name`·`identifier_name` 등 SwiftLint 표준 룰)은 도구로 잡고, 의미 기반(약어 금지, 역할 접미사 일관성)은 리뷰가 본다.
- **가정**: 대상 프로젝트에 SwiftLint/SwiftFormat 설정이 아직 없다(lint 게이트=가정). 설정을 도입하기 전까지 위 케이스·길이 규칙도 리뷰가 본다. 도입 시 룰명은 프로젝트 `.swiftlint.yml` 실측 후 확정한다.

## 도입 시 (현재 미채택)

SwiftUI·Coordinator는 대상 프로젝트가 채택하지 않는다(UI=UIKit 단독). 향후 도입 시에만 아래 접미사를 적용한다.

- `*View`(SwiftUI `View`), `*ViewModel`(화면 상태/로직), `*Coordinator`(화면 전환), `*Route`/`*Destination`(전환 목적지 enum).
