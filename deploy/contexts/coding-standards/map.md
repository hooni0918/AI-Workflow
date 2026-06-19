# coding-standards

## 역할

iOS(Swift · UIKit · Clean Architecture/DDD · SPM) 코딩 컨벤션의 인덱스. 두 종류로 구성된다:

- **rules** (`rules/`): "~해라, ~금지" 형태의 텍스트 규칙. AI가 코드를 대조할 때 참조한다. 중간 모델(예: sonnet)도 기계적으로 대조 가능한 수준으로 적는다.
- **principles** (`principles/`): 응집도·결합도·아키텍처 경계처럼 판단이 필요한 기준. 최상위 모델(예: opus) 판단을 전제한다.

같은 주제라도 역할이 다르므로 양쪽에 공존할 수 있다.

프로젝트 고유의 정확한 레이어·경계는 대상 프로젝트에 `.claude/docs/clean-architecture.md`가 있으면 그것을 1차 출처로 따른다. 이 디렉토리는 Clean Architecture/DDD·SPM '방법론'을 담고, 프로젝트별 레이어 정의는 그 파일에 위임한다.

기술 사실(SPM dependencies 레이어 대조, stub 검증 한계, `@Observable` 도입 조건, Swift 6 strict concurrency 강제 조건)은 이 디렉토리가 단일 출처가 아니다. [testing-strategy/assumptions.md](../testing-strategy/assumptions.md)가 단일 출처이고, 이 디렉토리의 규칙이 그 사실에 기대면 본문 재기술 대신 그 파일을 가리킨다.

## 로드 규칙

- 회사(실무) 프로젝트: `universal/` 만
- 개인 프로젝트: `universal/` + `personal/`

`universal/`은 팀원 누구나 동의할 범용 규칙, `personal/`은 네이밍·아키텍처처럼 작성자 개인 기준이다.

### 탐색 절차

1. 이 문서 하단의 rules·principles 파일 리스트를 훑고, 현재 작업과 관련된 파일을 선별한다.
2. 리뷰·구현 대상이 기존 코드베이스 위에서 도는 작업이면, 같은 역할을 하는 기존 패턴(UseCase 구조, Repository 레이어, 재사용 컴포넌트 등)을 코드베이스에서 직접 탐색해 참조한다 — 같은 것을 두 번 설계하지 않기 위함이다.
3. 선별한 파일을 모두 Read한다. 파일명만 보고 판단하지 않는다.
4. 매칭되는 규칙·패턴이 있으면 그 기준을 엄격하게 따른다. 프로젝트 상황과 맞지 않아 판단이 어려운 부분은 임의로 변형하지 않고 사용자에게 확인한다.

## 정적분석 사다리

코드 컨벤션은 강제 메커니즘이 강한 순서로 시도한다 — **정적분석(SwiftLint·SwiftFormat·SPM `Package.swift` dependencies 대조) → hook → 프롬프트 규칙**. 정적분석은 사람·CI·다른 도구 어디서나 걸리고, hook은 에이전트 런타임 안에서만 발동하기 때문이다. 아래 규칙 중 SwiftLint·SwiftFormat·각 모듈 `Package.swift`의 dependencies 배열 grep 대조로 기계 대조 가능한 항목은 각 파일 본문에 그 도구를 명시한다.

## 태그

| 태그 | 의미 | 사용 시점 |
|------|------|-----------|
| `file-folder-structure` | 파일·폴더 분리, 모듈 경계 기준 | 구현 구조·모듈 설계 시 |

## rules (중간 모델 이상 대조 가능, e.g. sonnet)

rules/universal/swift/general.md
rules/universal/uikit/basics.md
rules/universal/swiftui/basics.md (현재 미채택 — MINO는 UIKit/Clean Arch; 향후 도입 시 적용)
rules/personal/naming.md
rules/personal/clean-architecture/layer-rules.md [file-folder-structure]
rules/personal/spm/modularization.md [file-folder-structure]
rules/personal/coordinator/navigation.md (현재 미채택 — MINO는 UIKit/Clean Arch; 향후 도입 시 적용)

## principles (최상위 모델 판단 필요, e.g. opus)

principles/personal/architecture/clean-architecture.md
principles/personal/architecture/coordinator.md (현재 미채택 — MINO는 UIKit/Clean Arch; 향후 도입 시 적용)
principles/universal/swiftui/readability.md (현재 미채택 — MINO는 UIKit/Clean Arch; 향후 도입 시 적용)
principles/universal/swiftui/maintainability.md (현재 미채택 — MINO는 UIKit/Clean Arch; 향후 도입 시 적용)
