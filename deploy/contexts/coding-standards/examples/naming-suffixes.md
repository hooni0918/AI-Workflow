> **예시 (참고용).** Clean Architecture/DDD 아키텍처와 UIKit 프레임워크를 쓰는 프로젝트의 예시다. 마스터 표준이 아니며, 네 프로젝트의 .claude/docs에 네 것으로 정의해 대체하라.

# 역할 접미사 (Clean Arch + DDD + UIKit)

역할이 드러나도록 접미사를 일관되게 붙인 예시다. `<도메인>`·`<Entity>`·`<동사>`는 자리표시자이며, 실제 도메인 명사·동사로 채운다. 이 접미사 집합은 이 스택의 한 가지 선택일 뿐이고, **네 프로젝트의 접미사 집합으로 대체**한다.

- **화면**: `<도메인>ViewController` (UIKit `UIViewController`, 코드 기반 `NSLayoutConstraint` AutoLayout).
- **UseCase**: `<동사>UseCase`(protocol) + `Default<동사>UseCase`(구현)의 쌍. 단일 진입 메서드는 `execute`로 통일한다. UI 관심사를 두지 않는다.
- **Repository**: `<Entity>Repository`(protocol, Domain 레이어) + `<Entity>RepositoryImpl`(구현, Data 레이어, `final class`).
- **DTO**: `<Entity>DTO` (Data 레이어 `internal`, Domain에 노출 금지).
- **Entity / ValueObject**: Entity는 도메인 명사 그대로(`struct`), 식별자 VO는 `<Entity>ID`.
- **에러**: 도메인 오류는 `DomainError`, 인프라 오류는 `NetworkError`. 인프라 오류는 Data 레이어에서 `DomainError`로 번역한다(Domain은 `NetworkError`를 보지 못한다).
- **DesignSystem 토큰**: `App` 접두 enum(`AppColors`, `AppTypography`). 컴포넌트는 역할명(`TitleLabel`).

> 레이어별 import·경계, DTO 노출 금지, Anti-Corruption 같은 **경계 규칙의 1차 출처**는 네 프로젝트의 `.claude/docs`다(예: `architecture.md`, `layer-rules.json`). 그 정의가 있으면 그것을 따르고, 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행한다. 여기서는 네이밍 형태만 예시로 보인다.
