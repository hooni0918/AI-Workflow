# SPM 빌드·검증 명령 (단일 출처)

ios-workflow의 step·하위 스킬이 빌드·테스트·정적 검사 명령이 필요할 때 가리키는 단일 출처다. 어느 명령을 어느 시점에 쓰는지를 여기서 정한다. 명령 자체의 전제(빌드 오라클·테스트 분기·레이어 검증이 잡는 범위)는 [testing-strategy/assumptions.md](../../../contexts/testing-strategy/assumptions.md)가 진실 원천이다.

## 명령

| 용도 | 명령 |
|---|---|
| 빌드 검증 (오라클) | `xcodebuild build -project App/App.xcodeproj -scheme App -destination 'generic/platform=iOS Simulator'` |
| 테스트 (Core·Domain) | `cd Packages/<P> && swift test` |
| 테스트 (Networking·Data·DesignSystem·Feature) | `cd Packages/<P> && xcodebuild test -scheme <P> -destination 'platform=iOS Simulator,id=<UDID>'` |
| SwiftLint 기계 판정 (가정) | `swiftlint lint --strict` |

> 테스트 시뮬레이터 UDID는 `xcrun simctl list devices available`로 조회한다 — name 단독 지정은 동명 중복 위험이 있다. App 타깃엔 테스트 번들이 없으므로 앱레벨 테스트는 없다.

## 어느 시점에 무엇을

- **로직 검증의 진실 원천**은 테스트 실행 결과다. AI 산출물(테스트 매핑표 등)을 검증 기준으로 쓰지 않는다.
- **stub 커밋 게이트**: stub 커밋 전 빌드 오라클을 통과시킨다.
- **레이어 검증은 빌드와 별개**: 빌드 통과는 레이어 단방향을 보증하지 않는다. dependencies에 역방향을 적으면 컴파일은 통과하므로, 각 `Package.swift`의 dependencies 배열을 레이어 규칙과 grep 대조하는 절차를 따로 둔다. 무엇을 어떻게 대조하는지는 [spm-module/conventions/deps-verify.md](../../spm-module/conventions/deps-verify.md)가 절차 단일 출처다.

## 영역 한정

`swiftlint --fix` 같은 자동 수정은 본 PR 영역에만 적용한다. 인자 없이 전역 자동 수정하지 않는다 — PR 외 파일을 일괄 변경해 글로벌 룰 「내 작업 외 변경은 커밋하지 않는다」를 위반한다.
