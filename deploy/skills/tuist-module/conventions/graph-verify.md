# 그래프 검증 — 2-track 절차

빌드와 **독립된** 두 검사로 그래프 규칙 준수를 증명하는 절차다. APPLY 4·5단계가 이 문서를 따른다.

> 빌드·검사 명령(`tuist xcodebuild build`, `tuist inspect`, `tuist graph`)과 Tuist 버전 가정·deprecated 사유의 단일 출처는 [testing-strategy/assumptions.md](../../../contexts/testing-strategy/assumptions.md)다. 이 문서는 두 검사를 **어떻게 운용해 판정하는가**의 절차만 담는다.

## 왜 빌드와 분리하는가

빌드(`tuist xcodebuild build`)는 "manifest에 선언된 의존 안에서 타입이 맞는다"만 증명한다. 다음은 빌드가 통과해도 위반이다:

- 역방향 의존을 manifest에 선언 → 컴파일됨, 단방향 규칙 위반.
- 수평(동일 레이어) 의존을 manifest에 선언 → 컴파일됨, 격리 위반.

따라서 빌드 통과를 그래프 검증의 근거로 쓰지 않는다. 또한 자기가 작성한 manifest·설계서를 검증 기준으로 쓰면, 그 산출물에 박힌 위반을 같은 기준으로 검사해 통과시킨다(자기증명 루프). 검증 기준은 1차 소스 — [module-layers.md](module-layers.md)의 규칙과 `tuist graph`의 실제 위상이다.

## 두 도구가 잡는 것이 다르다

| 도구 | 잡는 것 | 안 잡는 것 |
|---|---|---|
| `tuist inspect` (track A) | 소스가 import 하지만 manifest에 **선언 안 한 import** (manifest↔소스 정합) | 레이어 방향. 선언만 돼 있으면 역방향이어도 통과 |
| `tuist graph` (track B) | 모듈 간 **실제 의존 위상** → 레이어 역방향·수평·사이클 | 소스의 미선언 import (선언된 의존만 그래프에 나타남) |

잡는 대상이 겹치지 않으므로 **둘 다** 실행한다. 하나만으로 "그래프 검증 완료"라 하지 않는다.

## track A — 미선언 import 검출

```bash
tuist inspect implicit-imports
```

(가정: Tuist 4.x. 하위 명령 이름은 버전에 따라 다를 수 있으므로 `tuist inspect --help`로 확인)

판정·처리:

1. 출력에 미선언 import가 0건이면 track A 통과.
2. 검출되면 각 항목을 [module-layers.md](module-layers.md) 방향 규칙과 대조한다.
   - 그 의존이 **허용 방향**이면 → manifest 의존 목록에 선언해 정합을 맞춘다.
   - **허용 안 되는 방향**(역방향·수평)이면 → manifest에 추가하지 말고 **소스의 import를 제거**하고, 필요한 타입은 하위 레이어로 내려 다시 의존한다.
3. "빌드 통과시키려고 일단 선언"은 금지. 방향이 틀린 import를 선언으로 덮으면 track B에서 잡히거나, 더 나쁘게는 통과해 그래프를 오염시킨다.

## track B — 레이어 단방향 위상 대조

```bash
tuist graph
```

판정·처리:

1. 출력(DOT/이미지/json 등 버전별 형식)에서 모듈 간 edge를 추출한다.
2. 각 edge의 방향을 [module-layers.md](module-layers.md) 「허용 의존 방향」과 대조한다.
   - **역방향 0건**: 하위 레이어가 상위를 의존하는 edge 없음.
   - **수평 0건**: 동일 레이어 모듈 간 직접 edge 없음.
   - **사이클 0건**: 자기 자신으로 돌아오는 경로 없음.
3. 위반 edge가 있으면 [module-layers.md](module-layers.md) 「흔한 위반과 교정」으로 고치고, APPLY 3단계(빌드)부터 재실행한다.
4. 대조 기준은 `tuist graph` 실제 출력 + conventions 규칙이다. PLAN 설계서를 기준으로 삼지 않는다.

## 검증 통과 판정

- track A 통과(미선언 import 0건 또는 모두 허용 방향으로 선언 정리) **AND** track B 통과(역방향·수평·사이클 0건)일 때만 "그래프 검증 통과".
- 종료 보고에 두 track 결과를 **분리해서** 적는다 (한 줄로 뭉뚱그리지 않는다). 어느 track이 무엇을 통과시켰는지 사용자가 구분할 수 있어야 한다.

## 가정 라벨

- 하위 명령 이름·출력 형식은 Tuist 버전 의존 → 미확인 시 "Tuist 4.x 가정" 표기.
- 스냅샷 검증을 끼울 경우, 검증 단계에서는 오라클(diff 시 fail). record 모드는 사람이 개입하는 별도 단계이며 검증 단계에서 돌리지 않는다.
