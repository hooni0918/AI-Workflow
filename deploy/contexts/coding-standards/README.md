# 코딩 스탠다드

iOS(Swift · UIKit · Clean Architecture/DDD · SPM) 개발에서 반복적으로 마주치는 판단들을 문서화한 기준 모음입니다.

## 다루는 기준

- **Swift 언어 규칙**: 강제 언래핑·force-try 금지, 접근제어 명시 등 정적분석으로 기계 대조 가능한 규칙
- **UIKit 작성 패턴**: `UIViewController` + 코드 기반 AutoLayout, DesignSystem 토큰 사용
- **네이밍**: Swift API Design Guidelines 기반
- **Clean Architecture/DDD 레이어 경계**: 레이어 단방향 의존, DDD 빌딩블록(Entity·UseCase·Repository), 인프라 오류 번역(Anti-Corruption)
- **SPM 모듈 구성**: 로컬 패키지 6층 레이어 의존 방향(Feature·Domain·Data·Networking·DesignSystem·Core)
- **코드 품질 원칙**: 가독성·유지보수성·아키텍처 경계 판단

> SwiftUI·Coordinator 규칙은 현재 미채택입니다(UI=UIKit · Clean Architecture). 향후 도입에 대비해 보존만 합니다.

## 상황에 맞는 기준 적용

모든 기준을 모든 프로젝트에 일률적으로 적용하지는 않습니다. 회사(실무) 프로젝트에서는 팀원 누구나 동의할 범용 기준(`universal/`)만 적용하고, 개인 프로젝트에서는 네이밍·아키텍처 등 더 세밀한 개인 기준(`personal/`)까지 적용합니다. 컨텍스트에 따라 적절한 수준의 기준을 선택하는 것도 엔지니어링 판단의 일부입니다.

## 강제 메커니즘 우선순위

규칙을 글로 적기 전에, 더 강한 강제 메커니즘으로 내릴 수 있는지 먼저 봅니다. 코드 컨벤션은 **정적분석(SwiftLint·SwiftFormat·SPM `dependencies` 대조) → hook → 프롬프트 규칙** 순으로 시도합니다. 정적분석으로 잡히는 것은 정적분석에 맡기고, 의미·맥락 판단이 필요한 것만 규칙 문서로 남깁니다. 인덱스와 로드 규칙은 [map.md](map.md)를 참고하세요.
