# Tuist 모듈화 규칙

새 화면·기능에 맞춰 모듈을 나눌 때의 경계와 의존 방향 규칙이다. 의존 그래프를 실제로 검증하는 도구·절차(`tuist inspect`·`tuist graph`의 2-track)는 [tuist-module 스킬](../../../../../skills/tuist-module/SKILL.md)이 단일 출처이고, 빌드·검사 명령 전제는 [testing-strategy/assumptions.md](../../../../testing-strategy/assumptions.md)가 단일 출처다. 이 문서는 "어느 방향이 맞는가"의 규칙만 정의한다.

## 레이어 경계: Feature / Core / Shared

모듈을 세 층으로 가른다. 의존은 **위에서 아래 한 방향**이다.

| 레이어 | 담는 것 | 의존 가능 대상 |
|---|---|---|
| **Feature** | 화면·플로우 단위 기능(`Feature/Profile`, `Feature/Settings`) | Core, Shared |
| **Core** | 도메인 로직·데이터(네트워크, 저장소, 도메인 모델) | Shared |
| **Shared** | 범용 유틸·디자인 시스템·확장 (도메인 무관) | (없음 — 최하위) |

- **역방향 금지**: Shared가 Core/Feature를, Core가 Feature를 의존하지 않는다.
- **수평 금지**: Feature 모듈이 다른 Feature 모듈을 직접 의존하지 않는다. 공유가 필요하면 그 부분을 Core/Shared로 내린다.
- **사이클 금지**: 의존이 자기 자신으로 돌아오는 경로를 만들지 않는다.

```
Feature ──→ Core ──→ Shared
```

## 도메인 종속 코드의 배치

특정 도메인에서만 쓰는 타입·유틸·컴포넌트는 `Shared`가 아니라 **그 도메인의 Feature/Core 모듈**에 둔다.

- **❌ bad**: Profile에서만 쓰는 `ProfileBadgeView`를 `Shared/DesignSystem`에 생성
- **✅ good**: `Feature/Profile` 안에 생성

`Shared`에는 **둘 이상의 도메인**이 공통으로 쓰는 것만 둔다. "언젠가 재사용할지 모른다"는 이유로 Shared에 올리지 않는다 — 끌어올린 순간 그 도메인을 떼어낼 수 없게 묶인다.

## 경계 타입은 하위 레이어에 둔다

두 모듈이 주고받는 경계 타입(도메인 모델, DTO, 프로토콜)은 의존 방향상 **하위 레이어**에 둔다. 상위가 정의한 타입을 하위가 의존하면 역방향이다.

## Project.swift 컨벤션

- 모듈 하나당 manifest의 `dependencies`에 **실제로 import하는 모듈만** 선언한다. 빌드를 통과시키려고 임시로 의존을 추가하지 않는다 — 미선언 import와 역방향 의존은 빌드가 아니라 그래프 검사가 잡는다(전제·도구는 위 cross-ref 참조).
- 모듈 타깃 이름·디렉토리 구조를 레이어와 일치시킨다(`Feature/`, `Core/`, `Shared/` 하위에 같은 이름). 이름만으로 레이어를 식별할 수 있어야 그래프 위반을 사람이 읽어낼 수 있다.
- 공통 설정(배포 타깃, Swift 버전, 빌드 세팅)은 manifest helper로 한 곳에 모은다. 모듈마다 복붙하지 않는다.
