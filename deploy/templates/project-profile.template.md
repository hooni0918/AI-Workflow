# 프로젝트 프로필 (project-profile)

> 이 파일을 사용 레포의 `.claude/docs/project-profile.md`로 복사해 채운다. 마스터 스킬이 이걸 읽어 적응한다.

마스터 표준은 특정 아키텍처/UI프레임워크/레이어/네이밍을 고르지 않는다. 그 구체 사실은 **사용 레포가 이 프로필로 공급**한다. 마스터 스킬·규칙은 "프로필에 해당 슬롯이 채워져 있으면 1차 출처로 따르고, 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행"한다.

아래 슬롯을 네 프로젝트 값으로 채운다. 채우지 않은 슬롯은 비워 두지 말고 `(미정)` 또는 `(미채택)`으로 표기해 "묻는다/가정한다" 분기를 명시한다.

## UI 프레임워크

<!-- 채우는 법: 이 프로젝트가 쓰는 UI 프레임워크를 적는다. 혼용 시 화면 종류별로 어디에 무엇을 쓰는지 한 줄 덧붙인다. -->

- **프레임워크**: `(예: UIKit / SwiftUI / 혼용)`
- **레이아웃 방식**: `(예: 코드 기반 AutoLayout / Storyboard / SwiftUI 선언형)`

## 모듈 시스템

<!-- 채우는 법: 모듈 구성 방식을 적는다. 다층 모듈이면 레이어 목록은 아래 "레이어 규칙 파일"에 위임하고 여기엔 시스템 종류만. -->

- **시스템**: `(예: 로컬 SPM 패키지 / Tuist / 단일 타깃)`
- **패키지 루트**: `(예: Packages/ — 단일 타깃이면 (해당 없음))`

## 빌드 오라클 명령

<!-- 채우는 법: "이게 통과하면 빌드 OK"의 정답 명령 한 줄. 스킬이 stub 커밋 게이트 등에서 이 명령을 빌드 오라클로 쓴다. -->

- **명령**: `(예: xcodebuild build -project App/App.xcodeproj -scheme App -destination 'generic/platform=iOS Simulator')`

## 테스트 명령

<!-- 채우는 법: 테스트 러너 명령. 모듈/레이어별로 러너가 갈리면 행을 나눠 적는다. 시뮬레이터 UDID 조회 절차가 필요하면 한 줄 덧붙인다. -->

| 대상 | 명령 |
|---|---|
| `(예: 순수 로직 패키지)` | `(예: cd Packages/<P> && swift test)` |
| `(예: UI 의존 패키지)` | `(예: cd Packages/<P> && xcodebuild test -scheme <P> -destination 'platform=iOS Simulator,id=<UDID>')` |

- **시뮬레이터 UDID 조회**: `(예: xcrun simctl list devices available — 미사용이면 (해당 없음))`

## 레이어 규칙 파일 (layer-rules.json)

<!-- 채우는 법: 레이어 목록·의존 허용 방향을 기계 대조 가능한 형태로 둔 파일 경로. 마스터는 레이어를 고르지 않으므로, 이 파일이 레이어·경계의 1차 출처다. -->

- **경로**: `(예: .claude/docs/layer-rules.json — 없으면 (미정))`
- **대조 메커니즘**: `(예: 각 Package.swift의 dependencies 배열 grep 대조 / Tuist graph / (미정))`

## 아키텍처 문서 경로 (architecture.md)

<!-- 채우는 법: 이 프로젝트의 아키텍처·레이어·경계의 산문 정의가 있는 문서 경로. 레이어 정의가 마스터 방법론과 어긋나면 이 문서를 따른다. -->

- **경로**: `(예: .claude/docs/architecture.md — 없으면 (미정))`
- **아키텍처**: `(예: Clean Architecture/DDD / MVVM / TCA / (미정))`

## 네이밍 규약 요약

<!-- 채우는 법: 이 프로젝트가 강제하는 네이밍 규약을 한 줄 요약 + 강제 메커니즘. 세부 규칙이 별도 문서에 있으면 경로로 위임한다. -->

- **요약**: `(예: Swift API Design Guidelines 기반. UseCase 접미사·Repository 접미사 등 레이어 접미사 규약은 architecture.md 참조)`
- **강제 메커니즘**: `(예: SwiftLint 커스텀 룰 / 프롬프트 규칙 / (미정))`

## 미채택·예외

<!-- 채우는 법: 마스터 표준 중 이 프로젝트가 의도적으로 미채택하거나 변형하는 항목을 적는다. 빈 항목이면 "(없음)". -->

- `(예: 스냅샷 테스트 미채택 / Coordinator 미채택 / (없음))`
