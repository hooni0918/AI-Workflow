# 모듈 레이어 — 경계와 의존 방향

레이어 배치·허용 의존 방향의 **단일 출처**다. PLAN의 배치·방향 설계와 APPLY의 track B 검증이 모두 이 문서를 기준으로 한다.

## 레이어 정의

위에서 아래로 의존이 흐른다. 위가 더 자주 바뀌는(휘발성 높은) 쪽, 아래가 더 안정적인 쪽이다.

| 레이어 | 책임 | 예 |
|---|---|---|
| **Feature** | 화면, 사용자 흐름, 화면 상태(ViewModel/Store), 화면 단위 네비게이션 | `SearchFeature`, `AuthFeature`, `SettingsFeature` |
| **Domain** | 화면과 무관한 도메인 규칙·엔티티·유스케이스·리포지토리 인터페이스 | `SearchDomain`, `AuthDomain` |
| **Core** | 레이어 무관 공용 기반 (네트워킹, 디자인 토큰/시스템, 공용 확장, 로깅, 저장소 구현 등) | `NetworkCore`, `DesignCore`, `LoggingCore` |

레이어 수·이름은 레포마다 다를 수 있다. 추가 레이어(예: `Shared`, `App`)가 있으면 이 표에 그 책임·휘발성 위치를 추가하고, 아래 방향 규칙을 그에 맞춰 확장한다. (가정: 위 3계층은 기본형이며, 실제 레포 레이어는 `tuist graph`·디렉토리 구조로 확인)

## 허용 의존 방향

### 1. 단방향 (상위 → 하위만)

```
Feature ──→ Domain ──→ Core
Feature ──────────────→ Core   (Feature가 Core 직접 의존은 허용)
```

- Feature는 Domain·Core를 의존할 수 있다.
- Domain은 Core를 의존할 수 있다.
- **하위는 상위를 의존하지 않는다.** Domain → Feature, Core → Domain/Feature 는 모두 금지(역방향).

### 2. 수평 의존 금지

- 같은 레이어 모듈끼리 직접 의존하지 않는다. `FeatureA ↛ FeatureB`, `DomainA ↛ DomainB`.
- 공유가 필요하면 공유 부분을 **하위 레이어로 내려** 거기서 의존한다. 예: 두 Feature가 같은 모델을 쓰면 그 모델을 Domain(또는 Core)에 두고 각 Feature가 그것을 의존한다.

### 3. 사이클 금지

- 어떤 경로로도 의존이 자기 자신으로 돌아오지 않는다. A → B → A, A → B → C → A 모두 금지.

## 경계 판정 — 모듈을 어디에 둘까

새 모듈·분리 대상을 배치할 때:

1. **하는 일 한 줄**을 적는다.
2. "화면·사용자 흐름이 보이는가?" → 보이면 Feature.
3. "화면 없이 도메인 규칙·엔티티만 다루는가?" → Domain.
4. "레이어와 무관하게 어디서나 쓰일 기반인가?" → Core.
5. 애매하면 **더 하위(더 의존받는) 레이어로 내리는 쪽**을 우선 검토한다 — 상위는 교체가 싸고, 하위로 잘못 내린 것은 의존자가 생긴 뒤 되돌리기 비싸다.

## 흔한 위반과 교정

| 위반 | 증상 | 교정 |
|---|---|---|
| 역방향 | Domain이 Feature를 import | 끌어쓰던 타입을 Domain/Core로 내리고 의존 뒤집기 |
| 수평 | FeatureA가 FeatureB를 import | 공유 부분을 Domain/Core로 추출해 양쪽이 그것을 의존 |
| Core 비대 | Core가 특정 Feature 전용 로직을 가짐 | 그 로직을 해당 Domain/Feature로 올림 |
| 우회 사이클 | A→B→C→A 형태 | 사이클을 끊는 추상(인터페이스)을 하위 레이어에 두고 의존 역전 |

## 빌드가 못 잡는다는 점

위 방향 규칙은 **모두 manifest에 선언하면 컴파일러를 통과한다.** 역방향·수평 의존을 manifest에 적으면 빌드는 초록불이 된다. 그래서 방향 준수는 빌드가 아니라 [graph-verify.md](graph-verify.md)의 track B(`tuist graph` 위상 대조)로 검증한다.
