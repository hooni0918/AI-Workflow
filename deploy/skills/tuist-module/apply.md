# APPLY — 생성 + 빌드 + 검증 2-track

SKILL.md 「작업 진행 순서」의 APPLY 세션 본문이다. PLAN의 설계서·manifest 변경안을 적용 지시서로 받아 파일을 만들고 빌드한 뒤, 빌드와 **독립된** 두 검사로 그래프 규칙 준수를 증명한다.

진입 시 SKILL.md 「[CRITICAL] 지킬 원칙」, [conventions/module-layers.md](conventions/module-layers.md), [conventions/graph-verify.md](conventions/graph-verify.md)를 먼저 읽는다.

## 0. 입력 확인

PLAN 산출물(그래프 설계서·manifest 변경안)을 읽는다. 없으면 진행하지 않고 사용자에게 PLAN 선행을 안내한다 — 검증 기준이 없는 채로 적용하면 "무엇을 어겼는지" 판정할 근거가 없다.

- 설계서를 **적용 지시·인덱스**로 읽는다. 검증 기준으로 읽지 않는다 (SKILL.md 「검증 기준 = 진실 원천」).
- 현재 그래프를 다시 확인한다: `tuist graph` (PLAN이 본 "before"와 달라졌을 수 있으므로 재확인).

## 1. manifest 반영

PLAN의 manifest 변경안을 실제 manifest 파일(`Project.swift` 등)에 반영한다.

- 변경안 diff 그대로 적용한다. APPLY가 임의로 의존을 추가·삭제하지 않는다 — 그래프는 PLAN이 설계한 것이다. 적용 중 PLAN 설계가 빌드 불가임이 드러나면(예: 누락된 하위 모듈) 임의 보정하지 말고 사용자에게 보고한다 (「입력 산출물 비판적 검토」에 준해 결정 위임 형태로).

## 2. 모듈 디렉토리·소스 스켈레톤 생성

레포의 모듈 디렉토리 관례에 맞춰 디렉토리와 최소 소스를 만든다.

- 디렉토리 구조·소스 배치는 기존 형제 모듈의 관례를 미러링한다 (Sources/, Tests/, Resources/ 등 레포 실제 구조 확인).
- 공개 타입은 **stub**으로 만든다. stub 규칙은 SKILL.md 「stub은 시그니처 정합만 보증한다」를 따른다:
  - 공개 시그니처는 의존 모듈이 컴파일되도록 갖춘다.
  - **빈 함수 본체는 컴파일러가 미구현을 못 잡는다** — 본체 미구현 항목을 종료 보고에 명시한다.
  - **저장 프로퍼티·`@Published` 초기값은 `fatalError`로 못 메운다.** 저장 상태가 있는 타입은 더미 초기값을 박거나 본체 구현으로 미룬다.
  - `@Observable`을 쓰는 stub은 deployment target이 iOS 17+인지 확인한다 (미확인이면 "iOS 17+ 가정" 라벨, SKILL.md).

## 3. 빌드

```bash
tuist xcodebuild build
```

- 정답 빌드 명령은 `tuist xcodebuild build`다. `tuist build`는 4.x에서 deprecated이므로 쓰지 않는다 (가정: Tuist 4.x).
- 빌드 실패 시 원인을 분류한다:
  - **시그니처 불일치**: stub 시그니처가 의존자 기대와 안 맞음 → stub 시그니처 수정.
  - **미선언 import**: 소스가 import 하나 manifest에 없음 → 4단계 `tuist inspect`가 정밀 검출하지만, 이 단계에서 드러나면 PLAN 설계 의존 범위 안에서 manifest를 교정하거나(설계 내) 설계 위반이면 사용자 보고.
- 빌드 통과는 "선언된 의존 안에서 타입이 맞는다"만 의미한다. **빌드 통과를 그래프 검증 통과로 보고하지 않는다** (SKILL.md 「빌드 성공 ≠ 그래프 규칙 준수」). 4·5단계 검증이 별도로 필요하다.

## 4. 검증 track A — 미선언 import (`tuist inspect`)

[conventions/graph-verify.md](conventions/graph-verify.md)의 track A 절차를 따른다.

```bash
tuist inspect implicit-imports
```

- 소스가 import 하지만 manifest 의존에 **선언되지 않은 import**를 검출한다 (manifest↔소스 정합).
- 검출되면: 그 import가 PLAN 설계 의존 방향에 부합하면 manifest에 선언, **부합하지 않으면(역방향·수평 등) import 자체를 제거**한다. 부합 여부 판정 기준은 [conventions/module-layers.md](conventions/module-layers.md)다 — 안 맞는데 manifest에 추가해 통과시키지 않는다.
- 이 검사는 **레이어 방향을 보지 않는다.** 방향 검증은 track B가 담당한다.

## 5. 검증 track B — 레이어 단방향 위상 (`tuist graph`)

[conventions/graph-verify.md](conventions/graph-verify.md)의 track B 절차를 따른다.

```bash
tuist graph
```

- 산출된 실제 의존 위상을 [conventions/module-layers.md](conventions/module-layers.md)의 허용 방향과 대조한다.
- 점검: 역방향 의존 0건 / 수평(동일 레이어 직접) 의존 0건 / 사이클 0건.
- 위반이 있으면 manifest·소스를 고치고 3단계부터 재실행한다. **위반을 "가정"으로 통과시키지 않는다** — 방향 위반은 사실 위반이다.
- 대조 기준은 `tuist graph` 실제 출력과 conventions 규칙이다. PLAN 설계서를 기준으로 대조하지 않는다 (자기증명 차단).

> track A와 B는 잡는 대상이 다르다 (정합 vs 방향). 둘 다 통과해야 그래프 검증 통과다. 하나만 돌리고 "검증 완료"라 보고하지 않는다.

## 6. (선택) 스냅샷·테스트

테스트 타겟이 있으면 `tuist test`로 돌린다 (가정: 테스트 타겟 존재 여부 미확인 시 사용자 확인).

- 스냅샷 테스트가 있으면 검증 단계에서는 **오라클**로 쓴다 — 기존 레퍼런스와 diff 시 fail. record(레퍼런스 갱신)는 사람이 개입하는 별도 단계이므로 검증 단계에서 record 모드로 돌리지 않는다 (SKILL.md).

## 7. 종료 보고

다음을 보고한다.

- 생성한 모듈·디렉토리, 반영한 manifest 변경
- 빌드 결과 (`tuist xcodebuild build` 통과/실패)
- **검증 2-track 결과 분리 명시**: track A(`tuist inspect`, 미선언 import) 결과 / track B(`tuist graph`, 레이어 방향) 결과. 둘 다 통과해야 "그래프 검증 통과".
- **stub 한계 명시**: 시그니처·그래프만 보증, 빈 본체 미구현 목록. 저장 프로퍼티 더미 초기값을 박은 곳.
- 남은 "가정" 라벨 (확인 못 한 Tuist 버전·target·strict mode·테스트 등)
- 본체 구현은 이 스킬 범위 밖임을 안내한다.
