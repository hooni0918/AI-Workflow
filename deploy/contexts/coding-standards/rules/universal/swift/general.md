# Swift 일반 규칙

SwiftLint·SwiftFormat으로 기계 대조 가능한 규칙을 모은다. 각 규칙에 대응하는 린트 룰을 함께 적어, 리뷰어가 프롬프트 판단 대신 도구 실행으로 검출하도록 한다.

> 도구 실행 명령(`swiftlint lint --strict` 등)과 검출 범위 전제는 [testing-strategy/assumptions.md](../../../../testing-strategy/assumptions.md)가 단일 출처다. 여기서는 어떤 패턴을 금지하는지만 정의한다.

## 강제 언래핑 금지

옵셔널을 `!`로 강제 언래핑하지 않는다. `guard let` / `if let` / `??` 로 안전하게 푼다. `!`는 nil일 때 런타임 크래시이므로, 컴파일러가 막아 주지 않는 사고를 코드에 심는 것이다.

- **기계 대조**: SwiftLint `force_unwrapping` 룰.
- **예외**: 테스트 코드의 `XCTUnwrap` 대체, IBOutlet 등 프레임워크가 강제하는 자리만. 그 외 예외가 필요하면 사용자에게 근거를 들어 승인받는다.

```swift
// ❌ bad — nil이면 크래시
let url = URL(string: urlString)!

// ✅ good
guard let url = URL(string: urlString) else { return }
```

## force-try 금지

`try!`로 에러를 무시하지 않는다. `do/catch` 또는 `try?`로 실패를 표현한다. `try!`는 throw 시 크래시다.

- **기계 대조**: SwiftLint `force_try` 룰.

```swift
// ❌ bad
let data = try! Data(contentsOf: fileURL)

// ✅ good
guard let data = try? Data(contentsOf: fileURL) else { return nil }
```

## 강제 캐스팅 금지

`as!` 다운캐스팅을 쓰지 않는다. `as?`로 받고 실패 경로를 명시한다.

- **기계 대조**: SwiftLint `force_cast` 룰.

## 접근제어 명시

타입·프로퍼티·메서드의 접근제어를 의도에 맞게 명시한다. 모듈 경계를 넘어 노출할 것만 `public`/`package`, 그 외는 `internal`(생략 가능) 또는 `private`/`fileprivate`로 좁힌다. 기본 `internal`에 의존해 모든 것을 열어 두지 않는다 — 모듈의 공개 계약이 흐려지면 Tuist 레이어 경계(아래 「모듈화」 참조)가 의미를 잃는다.

- **기계 대조**: SwiftLint `explicit_acl`·`explicit_top_level_acl` 룰(opt-in). 모듈이 라이브러리로 노출되는 경우 켠다.
- **가정**: 어떤 룰을 켜는지는 프로젝트 `.swiftlint.yml` 실측 후 확정. 위 룰명은 SwiftLint 표준 룰 기준.

## print 직접 호출 금지

배포 코드에서 `print`로 로깅하지 않는다. 프로젝트 로거(예: `os.Logger`)를 쓴다.

- **기계 대조**: SwiftLint `custom_rules`로 `print(` 패턴을 막거나, `no_print` 커스텀 룰. (가정: 커스텀 룰 등록 여부는 프로젝트별.)

## 포매팅은 SwiftFormat에 위임

들여쓰기, import 정렬, 공백, 줄바꿈 같은 포매팅은 사람·AI가 손으로 맞추지 않고 SwiftFormat이 강제한다. 리뷰에서 포매팅을 지적 항목으로 올리지 않는다 — 포매터가 단일 출처다.

- **영역 한정**: 자동 수정은 본 작업 영역에만 적용한다. 전역 일괄 수정은 PR 외 파일을 함께 바꿔 글로벌 룰 「내 작업 외 변경은 커밋하지 않는다」를 위반한다.
