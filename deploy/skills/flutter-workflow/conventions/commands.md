# flutter 빌드·검증 명령 (위임 지도)

flutter-workflow의 step·하위 스킬이 테스트·정적 검사·codegen·l10n·레이어 검증·앱 실행 명령이 필요할 때 가리키는 진입점이다. 어느 종류의 명령을 어느 시점에 쓰는지(방법)는 여기서 정한다.

원칙상 명령의 단일 출처는 프로젝트 프로필(`.claude/docs/project-profile.md`)이다. 다만 이 스킬은 qube 전용이므로 아래 **qube 실측 기본값**을 조작 기본값으로 제공한다. 프로필이 실측과 다르거나 비qube 프로젝트에 쓰이면 프로필을 우선하고, 프로필도 없으면 사용자에게 묻거나 `[가정]` 라벨로 진행한다.

**게이트형 빌드 오라클은 없다.** flutter는 컴파일 통과 하나로 정합을 보증하는 단일 빌드 게이트가 없다. 대신 정적 그물 = `flutter analyze`, 동작 그물 = `flutter test`, 배선·DI·bloc 확인 = `flutter run` + hot restart로 나눠 검증한다.

## 명령 종류 (qube 실측 기본값)

| 용도 | 명령 |
|---|---|
| 정적 검사 | `flutter analyze` |
| 테스트 | `flutter test <패키지 경로>` (예: `flutter test lib/feature/integration/qube/question`) |
| codegen | `dart run build_runner build --delete-conflicting-outputs` |
| l10n 생성/검사 | `flutter/l10n` 디렉토리에서 `dart run generate.dart [--check]` |
| 앱 실행 | `flutter run` (기기 선정은 `flutter devices` → `flutter run -d <id>`) |

- 위 값은 qube 실측 기본값이다. 다른 프로젝트에 쓰이면 프로젝트 프로필이 공급하는 값을 따른다.
- 저장소가 fvm으로 SDK를 고정하면 위 명령에 `fvm ` 프리픽스를 붙인다(예: `fvm flutter test ...`). qube 실측 현재 미사용.

### hot restart 규칙

`flutter run`으로 조립 결과를 확인할 때, 배선·DI(get_it)·bloc 초기화·`main()` 변경의 검증은 hot **reload**가 아니라 hot **restart**로 한다. hot reload는 `main()`/DI/bloc를 재초기화하지 않아 배선이 틀려도 거짓 통과한다.

## 어느 시점에 무엇을

- **로직 검증의 진실 원천은 테스트 실행 결과다** (`flutter test` green). AI 산출물(테스트 매핑표·체크리스트 등)을 검증 기준으로 쓰지 않는다.
- **테스트 TODO → 구현 전환 커버리지 게이트**: 테스트 TODO는 PLAN의 `implementation.md` 체크리스트로 관리한다(코드 골조 아님). IMPL 종료 시 그 체크리스트의 모든 테스트 TODO가 실제 테스트로 전환됐는지 대조한다.
- **golden 테스트**: record(생성)와 verify(검증)를 분리해 다룬다 `[가정]`.

## 레이어 검증 (analyze와 별개)

`flutter analyze` 통과는 레이어 단방향을 보증하지 않는다. `pubspec.yaml`의 `path:` 의존에 역방향을 적어도 `flutter pub get`/`analyze`는 통과하기 때문이다. 그래서 2-track으로 대조한다.

- **track A (미선언 import)**: `flutter pub get`/`flutter analyze`가 잡는다. 선언하지 않은 패키지를 import하면 해석 실패.
- **track B (선언됐지만 방향 위반)**: 각 `pubspec.yaml`의 `path:` 로컬 의존을 grep해 레이어 방향과 대조한다. 예: `grep -rn "path:" lib/**/pubspec.yaml`로 로컬 path 의존을 열거한 뒤 방향을 확인.

의도 방향(clean arch): `feature → domain ← data`. domain이 최내곽(feature·data 의존 금지)이고, core·design_system은 횡단이다.

정확한 허용 방향 표는 이 스킬이 단정하지 않는다. `review-checklist.md`의 리뷰 채굴 근거 + 코드베이스 실측(각 `pubspec.yaml`의 `path:` 의존)으로 확인한다.

실측 주의: 현재 `lib/domain/pubspec.yaml`에 `core` 의존이 있고, 리뷰에서 "도메인이 core 참조 금지"로 지적된 이력이 있다 — 레이어 위반이 과거 leak됐다. 신규·이관 작업 시 이 방향을 재확인한다.

## 기계 게이트 (step-4 실행)

analyze·test와 별개로, 커밋된 산출물이 최신 소스와 어긋나지 않는지 기계적으로 대조한다.

- **codegen drift**: `dart run build_runner build --delete-conflicting-outputs` 재실행 후 `git diff`가 0건이어야 한다. 커밋된 `*.g.dart`가 신선 산출물과 동일해야 한다는 뜻이다. (신규 DTO의 `.g.dart`를 커밋하는 것은 정상 — 기준은 "무변경"이 아니라 "재생성해도 동일".)
- **l10n drift**: 문구(`flutter/l10n/strings.yaml`)를 변경했으면 `flutter/l10n`에서 `dart run generate.dart --check`를 돌려 drift가 없는지 확인한다.
- **pubspec.lock**: 의도한 의존성 변경 외 diff는 0건이어야 한다. 무관 churn을 커밋하지 않는다(글로벌 룰 「내 작업 외 변경은 커밋하지 않는다」).

## 영역 한정

`dart fix --apply` 같은 일괄 자동 수정은 본 PR 영역에만 적용한다. 인자 없이 전역으로 자동 수정하지 않는다 — PR 외 파일을 일괄 변경해 글로벌 룰 「내 작업 외 변경은 커밋하지 않는다」를 위반한다.

---

- 팀 리뷰 규칙(레이어 방향 근거 포함)은 사이블링 `review-checklist.md`(로컬 전용 캐시)를 따른다.
- 정적 검사 룰 셋은 프로젝트 `flutter/analysis_options.yaml`을 진실 원천으로 한다.
