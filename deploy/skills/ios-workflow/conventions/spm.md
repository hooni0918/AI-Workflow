# SPM 빌드·검증 명령 (위임 지도)

ios-workflow의 step·하위 스킬이 빌드·테스트·정적 검사 명령이 필요할 때 가리키는 진입점이다. 어느 종류의 명령을 어느 시점에 쓰는지(방법)는 여기서 정한다. 실제 명령 문자열(빌드 오라클·테스트 명령·정적 검사 명령)은 마스터가 고르지 않고 프로젝트가 공급한다.

**명령의 단일 출처는 프로젝트 프로필 `.claude/docs/project-profile.md`다.** 빌드 오라클·테스트 명령(레이어/타깃별 분기 포함)·SwiftLint 호출 방식·시뮬레이터 선정 방법은 거기서 읽는다. 프로필이 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행한다. 명령이 잡는 범위의 전제(빌드 오라클·테스트 분기·레이어 검증이 보증하는 것)는 [testing-strategy/assumptions.md](../../../contexts/testing-strategy/assumptions.md)가 진실 원천이다.

## 명령 종류 (값은 프로젝트 프로필이 공급)

| 용도 | 출처 |
|---|---|
| 빌드 검증 (오라클) | 프로젝트 프로필이 정의 — 예: `xcodebuild build -project App/App.xcodeproj -scheme App -destination 'generic/platform=iOS Simulator'` |
| 테스트 (시뮬레이터 불필요 레이어) | 프로젝트 프로필이 정의 — 예: `cd Packages/<P> && swift test` |
| 테스트 (시뮬레이터 필요 레이어) | 프로젝트 프로필이 정의 — 예: `cd Packages/<P> && xcodebuild test -scheme <P> -destination 'platform=iOS Simulator,id=<UDID>'` |
| SwiftLint 기계 판정 | 프로젝트 프로필이 정의 — 룰 셋은 [templates/swiftlint.template.yml](../../../templates/swiftlint.template.yml)에서 출발 |

> 위 예시는 한 프로젝트의 구체값일 뿐 마스터의 단정이 아니다. 어느 레이어가 시뮬레이터를 요구하는지, 앱레벨 테스트 번들이 있는지, 테스트 시뮬레이터 UDID를 어떻게 조회하는지(예: `xcrun simctl list devices available` — name 단독 지정은 동명 중복 위험)는 프로젝트 프로필을 따른다.

## 어느 시점에 무엇을

- **로직 검증의 진실 원천**은 테스트 실행 결과다. AI 산출물(테스트 매핑표 등)을 검증 기준으로 쓰지 않는다.
- **stub 커밋 게이트**: stub 커밋 전 빌드 오라클을 통과시킨다.
- **레이어 검증은 빌드와 별개**: 빌드 통과는 레이어 단방향을 보증하지 않는다. dependencies에 역방향을 적으면 컴파일은 통과하므로, 각 `Package.swift`의 dependencies 배열을 레이어 규칙과 대조하는 절차를 따로 둔다. 기계 대조는 `check_spm_layers.py`(허용 방향은 프로젝트 `layer-rules.json`을 `--rules`로 공급)로 한다. 무엇을 어떻게 대조하는지는 [spm-module/conventions/deps-verify.md](../../spm-module/conventions/deps-verify.md)가 절차 단일 출처다.

## 영역 한정

SwiftLint 자동 수정(`--fix` 등) 같은 일괄 변경은 본 PR 영역에만 적용한다. 인자 없이 전역 자동 수정하지 않는다 — PR 외 파일을 일괄 변경해 글로벌 룰 「내 작업 외 변경은 커밋하지 않는다」를 위반한다.
