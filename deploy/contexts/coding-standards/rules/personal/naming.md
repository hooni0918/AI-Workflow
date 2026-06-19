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
items.map { t in t.title }
let vm = ProfileViewModel()

// ✅ good
items.map { topic in topic.title }
let viewModel = ProfileViewModel()
```

널리 굳은 약어(`url`, `id`, `html`)는 예외다. 약어의 대소문자는 통일한다(`userID`가 한 곳, `userId`가 다른 곳에 섞이지 않게).

## 타입·프로토콜·파일

- 타입(`struct`/`class`/`enum`)은 UpperCamelCase, 프로퍼티·메서드·인자는 lowerCamelCase.
- 능력을 나타내는 프로토콜은 `-able`/`-ible`/`-ing`(`Equatable`, `ProgressReporting`), 역할·명사형 프로토콜은 명사(`Collection`).
- 한 파일에 한 주(主) 타입을 두고 **파일명을 그 타입명과 일치**시킨다 (`ProfileView.swift` → `struct ProfileView`). 보조 확장·작은 헬퍼는 같은 파일에 둘 수 있다.

## SwiftUI / Coordinator 역할 접미사

역할이 드러나도록 접미사를 일관되게 붙인다.

- `*View` (SwiftUI `View`), `*ViewModel` (화면 상태/로직), `*Coordinator` (화면 전환 담당), `*Route`/`*Destination` (전환 목적지 enum).
- **기계 대조(부분)**: SwiftLint `type_name`·`identifier_name`으로 케이스·길이 규칙을 잡는다. 의미 기반(약어 금지, 역할 접미사)은 리뷰가 본다.
