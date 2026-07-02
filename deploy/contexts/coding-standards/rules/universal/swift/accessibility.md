# 접근성 식별자 규칙

인터랙션·검증 대상이 되는 UI 요소는 자동화 테스트와 VoiceOver 양쪽에서 다룰 수 있어야 한다. 이 파일은 그 식별자 부여 규칙을 정의한다.

> 접근성 요소 종류(버튼·입력 필드 등)와 프레임워크별 API(SwiftUI `accessibilityIdentifier(_:)` / UIKit `accessibilityIdentifier`)는 프로젝트가 UI 프레임워크에 따라 고른다. 여기서는 네이밍·역할 분리 규칙만 정의한다.

## accessibilityIdentifier ↔ accessibilityLabel 분리

- **accessibilityIdentifier**: UI 자동화(XCUITest, 외부 CLI 자동화 등)의 셀렉터. 사용자에게 노출되지 않는다.
- **accessibilityLabel**: VoiceOver 사용자가 듣는 설명. 화면에 보이는 사용자용이다.

둘을 혼동해 하나로 겸용하지 않는다 — 자동화 셀렉터가 지역화 문자열에 묶이면 문구 변경마다 테스트가 깨진다.

## 식별자 네이밍: 역할 기반, 표시 텍스트 금지

- 형식: `"<Screen>.<element>"` 계층형 (예: `"Login.emailField"`, `"Login.submitButton"`).
- `<element>`는 **역할**에서 온다(`submitButton`, `emailField`, `courseList`) — 화면에 표시되는 문구(`"로그인"`)를 식별자로 쓰지 않는다. 표시 텍스트는 지역화·문구 변경에 따라 바뀌지만 역할은 안 바뀐다.

```swift
// ❌ bad — 표시 텍스트에 결합, 지역화·문구 변경 시 깨짐
.accessibilityIdentifier("로그인")

// ✅ good — 역할 기반, 화면 접두사로 동명 충돌 방지
.accessibilityIdentifier("Login.submitButton")
```

## 부여 시점: 마크업 생성 시점

식별자는 뷰를 처음 작성하는 시점에 함께 부여한다. 화면을 다 만든 뒤 별도 "접근성 패스"로 사후 추가하지 않는다 — 사후 패치는 인터랙션 요소를 빠뜨리기 쉽고, 이미 리뷰가 끝난 마크업을 다시 건드리게 만든다.

대상: 버튼·입력 필드·토글·탭 제스처가 붙은 행·네비게이션 링크 등 인터랙션 요소, 그리고 로딩/빈/에러 상태처럼 자동화가 화면 상태를 구분해야 하는 검증 대상 표시.

- **기계 대조**: 식별자 존재 여부(요소당 identifier 부여)는 프로젝트가 커스텀 SwiftLint 룰이나 UI 테스트 실행 시점 스캐너로 강제할 수 있다 — 표준 SwiftLint 룰셋에는 없다(가정: 커스텀 룰 등록 여부는 프로젝트별). 네이밍이 역할 기반인지는 의미 판단이라 기계 대조가 어렵고 리뷰가 담당한다.
