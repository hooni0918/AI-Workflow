# 의존 검증 — 2-track 절차

빌드와 **독립된** 두 검사로 레이어 규칙 준수를 증명하는 절차다. APPLY 4·5단계가 이 문서를 따른다.

> 빌드 명령은 프로젝트 빌드 오라클([ios-workflow/conventions/spm.md](../../ios-workflow/conventions/spm.md))이 1차 출처이고, 검사 명령·도구 가정의 단일 출처는 [testing-strategy/assumptions.md](../../../contexts/testing-strategy/assumptions.md)다. 이 문서는 두 검사를 **어떻게 운용해 판정하는가**의 절차만 담는다.

## 왜 빌드와 분리하는가

빌드(프로젝트 빌드 오라클)는 "각 `Package.swift` `dependencies`에 선언된 의존 안에서 타입이 맞는다"만 증명한다. 다음은 빌드가 통과해도 위반이다:

- 역방향 의존을 `dependencies`에 선언 → 컴파일됨, 단방향 규칙 위반.
- 수평(동일 레이어) 의존을 `dependencies`에 선언 → 컴파일됨, 격리 위반.

따라서 빌드 통과를 의존 검증의 근거로 쓰지 않는다. 또한 자기가 작성한 `Package.swift`·설계서를 검증 기준으로 쓰면, 그 산출물에 박힌 위반을 같은 기준으로 검사해 통과시킨다(자기증명 루프). 검증 기준은 1차 소스 — [module-layers.md](module-layers.md)의 규칙이다.

## 두 검사가 잡는 것이 다르다

| 검사 | 잡는 것 | 안 잡는 것 |
|---|---|---|
| import↔선언 정합 (track A) | 소스가 import 하지만 `dependencies`에 **선언 안 한 import** (SPM이 빌드 오라클의 컴파일 실패로 강제) | 레이어 방향. 선언만 돼 있으면 역방향이어도 통과 |
| 선언↔레이어 규칙 (track B) | `dependencies` 배열의 **선언된 의존** → 레이어 역방향·수평·사이클 | 소스의 미선언 import (그건 컴파일이 잡는다) |

잡는 대상이 겹치지 않으므로 **둘 다** 실행한다. 하나만으로 "의존 검증 완료"라 하지 않는다.

## track A — 미선언 import 검출

프로젝트 빌드 오라클([ios-workflow/conventions/spm.md](../../ios-workflow/conventions/spm.md))을 실행한다. 빌드 명령 자체는 거기서 정한다(프로젝트 프로필이 1차 출처).

SPM은 `dependencies`에 선언 안 한 모듈을 import하면 컴파일을 실패시킨다. 즉 빌드 성공 자체가 "모든 import가 선언돼 있다"의 증거다 — track A는 빌드 오라클이 대신 잡아준다.

판정·처리:

1. 빌드가 BUILD SUCCEEDED면 미선언 import 0건 → track A 통과.
2. "선언 안 됨" 류로 실패하면 그 import를 [module-layers.md](module-layers.md) 방향 규칙과 대조한다.
   - 그 의존이 **허용 방향**이면 → 해당 `Package.swift` `dependencies`에 선언해 정합을 맞춘다.
   - **허용 안 되는 방향**(역방향·수평)이면 → `dependencies`에 추가하지 말고 **소스의 import를 제거**하고, 필요한 타입은 하위 레이어로 내려 다시 의존한다.
3. "빌드 통과시키려고 일단 선언"은 금지. 방향이 틀린 import를 선언으로 덮으면 track B에서 잡히거나, 더 나쁘게는 통과해 의존 그래프를 오염시킨다.

## track B — 레이어 단방향 위상 대조

**1차(결정론적 게이트)**: 레이어 정적 검사기를 프로젝트 레이어 규칙으로 돌린다.

```bash
python3 check_spm_layers.py <packages_dir> --rules <프로젝트 layer-rules.json>
```

검사기가 각 `Package.swift`의 `dependencies`를 떠서 허용 방향과 대조하고, 역방향·수평·미허용·사이클이면 **종료코드 1로 차단**한다 — LLM·사람 판단 없이 동일하게 판정하므로 이 결과가 track B 통과의 근거다. `--rules`에는 프로젝트가 공급한 `layer-rules.json`(키=모듈, 값=그 모듈이 의존해도 되는 하위 모듈 목록)을 넘긴다. 이 파일이 없으면 프로젝트 레이어 규칙([module-layers.md](module-layers.md)가 가리키는 1차 출처)에서 허용표를 옮겨 만들거나 사용자에게 확인한다 — 임의의 레이어 목록을 채워 넣지 않는다.

**보조(육안 대조)**: 검사기가 못 도는 환경이거나 위반 위치를 직접 짚을 때, 각 `Package.swift`의 `dependencies`를 grep으로 떠 edge 목록을 만들어 같은 규칙과 대조한다.

```bash
grep -nE '\.package\(path:' Packages/*/Package.swift
```

판정·처리:

1. 검사기 exit 0(보조로 grep 대조 시 각 edge의 방향이 [module-layers.md](module-layers.md) 「허용 의존 방향」과 일치)이면 track B 통과다.
   - **역방향 0건**: 하위 레이어가 상위를 의존하는 edge 없음.
   - **수평 0건**: 동일 레이어 모듈 간 직접 edge 없음.
   - **사이클 0건**: 자기 자신으로 돌아오는 경로 없음.
2. 검사기가 exit 1로 막거나 위반 edge가 있으면 [module-layers.md](module-layers.md) 「흔한 위반과 교정」으로 고치고, APPLY 3단계(빌드)부터 재실행한다.
3. 대조 기준은 `Package.swift`의 실제 `dependencies` 선언 + 프로젝트 레이어 규칙이다. PLAN 설계서를 기준으로 삼지 않는다.

## 검증 통과 판정

- track A 통과(빌드 성공 = 미선언 import 0건) **AND** track B 통과(검사기 exit 0 = 역방향·수평·사이클 0건)일 때만 "의존 검증 통과".
- 종료 보고에 두 track 결과를 **분리해서** 적는다 (한 줄로 뭉뚱그리지 않는다). 어느 track이 무엇을 통과시켰는지 사용자가 구분할 수 있어야 한다.

## 가정 라벨

- 프로젝트에 `.claude/docs/clean-architecture.md`(레이어 규칙 단일 출처)가 있으면 그것을 1차 출처로 보고 레이어 목록·경계를 그에 맞춘다.
- 스냅샷 검증을 끼울 경우, 검증 단계에서는 오라클(diff 시 fail). record 모드는 사람이 개입하는 별도 단계이며 검증 단계에서 돌리지 않는다.
