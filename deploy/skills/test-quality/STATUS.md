# test-quality 상태

초안이다. 게이트는 회귀 검증(`make verify-test-quality`)과 결제 예제 실측을 통과했지만, 실제 앱에는 아직 적용하지 않았다. 아래가 남은 일이다.

## 실제 앱 적용 (Team-MINO-iOS Domain 1차)

- 앱 레포에 `.test-quality/config.json`·프로필 「테스트 품질 검사」 슬롯·`.gitignore`(`.test-quality/result.json`) 추가
- CI 템플릿을 `.github/workflows/`로 옮기고 실제 GitHub Actions macOS 러너에서 실행 확인 — 템플릿은 로컬에서 단계별로만 확인했다
- 브랜치 보호에서 test-quality 잡을 필수 상태 검사로 지정, `.test-quality/`에 CODEOWNERS 리뷰 필수 지정
- 실행 시간과 보고서를 사용자와 확인 — 실측: 시뮬레이터 모듈 파일 하나(변이 10개)에 약 15분, 시뮬레이터 4대
- 실측에서 나온 Domain `NearbyPins.swift` 생존 변이 처리: 22번 줄 `<=`→`<`(정확히 3km 경계 — 테스트 주석상 부동소수 오차로 좌표 경유 재현 불가), 36번 줄 `<`→`<=`(앞의 `==` 분기 때문에 결과가 같은 변이 후보), 35번 줄 `>`→`>=`(같은 거리·같은 저장 시각 — 요구사항 미정)

## 확대

- 다른 모듈로 확대
- Flutter: 도구 미정. 후보 mutate4dart(Stryker 형식·`--diff` 지원, 2026-09 공개), mutation_test(컴파일 실패를 검출로 셈 — issue #34). 실측 후 정하고 flutter-workflow에 연결한다. 그 전에는 Flutter에 적용했다고 보고하지 않는다

## 알려진 제약

- swift-mutation-testing 1.5.1 이후 버전은 경계·산술 변이를 기본에서 뺐다. 올릴 때 `--operator-tier experimental`을 명시하고 결제 예제로 재실측한다
- 보호 훅은 `make sync-system` 전역 설치 경로에만 걸린다. 플러그인만 쓰는 환경의 강제는 앱 CI·CODEOWNERS가 맡는다
