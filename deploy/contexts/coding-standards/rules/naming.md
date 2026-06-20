# 네이밍 컨벤션

Swift API Design Guidelines를 기준으로 한다. 핵심은 **사용처(call site)에서 문장처럼 읽히는가**다.

이 문서는 *범용 네이밍 규율*만 정의한다. 어떤 역할 접미사 집합을 쓸지(`*ViewController`·`*UseCase`·`*RepositoryImpl` 등)는 마스터가 고르지 않는다 — **프로젝트의 `.claude/docs/project-profile.md`·`.claude/docs/architecture.md`가 그 접미사 집합과 네이밍 규약을 정의**한다. 여기서는 "프로젝트가 정한 집합을 일관되게 적용하라"는 규율만 강제한다.

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
let mgr = SessionManager()

// ✅ good
items.map { entity in entity.name }
let sessionManager = SessionManager()
```

널리 굳은 약어(`url`, `id`, `dto`)는 예외다. 약어의 대소문자는 통일한다(`userID`가 한 곳, `userId`가 다른 곳에 섞이지 않게).

## 타입·프로토콜·파일

- 타입(`struct`/`class`/`enum`)은 UpperCamelCase, 프로퍼티·메서드·인자는 lowerCamelCase.
- 능력을 나타내는 프로토콜은 `-able`/`-ible`/`-ing`(`Equatable`, `ProgressReporting`), 역할·명사형 프로토콜은 명사(`Collection`, `Iterator`).
- 한 파일에 한 주(主) 타입을 두고 **파일명을 그 타입명과 일치**시킨다. 보조 확장·작은 헬퍼는 같은 파일에 둘 수 있다.
- 한 타입에 붙는 확장만 모은 파일은 `Type+Extensions.swift`로 짓는다.

## 역할 접미사 일관성

역할이 드러나도록 접미사를 붙이고, **프로젝트가 정한 접미사 집합을 일관되게 적용**한다. 같은 역할에 두 가지 접미사가 섞이거나, 한 접미사가 서로 다른 역할에 재사용되지 않게 한다.

- 접미사 집합·각 접미사의 역할·레이어 배치(어떤 역할에 무슨 접미사를 붙이는가)는 **프로젝트의 `.claude/docs/project-profile.md`·`.claude/docs/architecture.md`가 1차 출처**다. 그 파일이 있으면 그것을 따른다.
- 프로젝트 문서가 없거나 해당 역할에 침묵하면, 임의로 접미사를 만들지 않고 코드베이스에서 같은 역할의 기존 패턴을 찾아 그것에 맞춘다. 기존 패턴도 없으면 사용자에게 확인한다(임의 가정 금지).
- 레이어별 import·경계, 노출 금지(예: DTO를 상위 레이어에 노출하지 않기), Anti-Corruption 같은 **경계 규칙**은 네이밍이 아니라 프로젝트의 `.claude/docs/architecture.md`·`layer-rules.json`이 정의한다. 여기서는 이름 형태만 다룬다.

> 구체 접미사 예시(`*ViewController`/`*UseCase`/`*RepositoryImpl` 등 특정 아키텍처·UI 프레임워크의 실측 접미사)는 마스터에서 분리해 `examples/naming-suffixes.md`에 참고용으로 두었다. 마스터 표준이 아니므로, 네 프로젝트의 접미사 집합은 네 `.claude/docs`에 정의해 쓴다.

## 기계 대조

- 케이스·길이 규칙(`type_name`·`identifier_name` 등 SwiftLint 표준 룰)은 도구로 잡고, 의미 기반(약어 금지, 역할 접미사 일관성)은 리뷰가 본다.
- **가정**: 프로젝트에 SwiftLint/SwiftFormat 설정이 없으면 위 케이스·길이 규칙도 리뷰가 본다(lint 게이트=가정 라벨). 설정을 도입하면 룰명은 프로젝트 `.swiftlint.yml`을 실측한 뒤 확정한다.
