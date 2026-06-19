# 모듈 레이어 — 경계와 의존 방향

레이어 배치·허용 의존 방향의 **단일 출처**다. PLAN의 배치·방향 설계와 APPLY의 track B 검증이 모두 이 문서를 기준으로 한다.

대상 프로젝트에 `.claude/docs/clean-architecture.md`가 있으면 그 문서를 레이어 목록·경계의 **1차 출처(single source)**로 보고 따른다. 이 문서는 SPM+Clean Architecture+DDD의 재사용 가능한 방법론을 담고, 프로젝트 고유의 정확한 레이어·경계는 그 문서에 위임한다. 충돌 시 프로젝트 문서가 우선한다.

## 레이어 정의

위에서 아래로 의존이 흐른다. 위가 더 자주 바뀌는(휘발성 높은) 쪽, 아래가 더 안정적인 쪽이다.

| 레이어 | 책임 | 허용 의존 |
|---|---|---|
| **App** | 컴포지션 루트, DI 조립(`AppDependencies`), 앱 진입·구성 | 전부 |
| **Feature** | 화면, 사용자 흐름, 화면 단위 네비게이션 (UIKit VC가 UseCase 직접 호출) | Domain, DesignSystem |
| **Data** | Repository 구현, DTO·인프라 연동, 인프라 오류→도메인 오류 번역 | Domain, Networking |
| **DesignSystem** | 디자인 토큰·공용 UI 컴포넌트 | Core |
| **Domain** | 도메인 규칙·엔티티·ValueObject·UseCase·Repository 인터페이스 | Core |
| **Networking** | 네트워크 전송·세션·요청 추상 | Core |
| **Core** | 레이어 무관 공용 기반 (공용 확장, 로깅, 유틸 등) | 없음 |

레이어 수·이름은 레포마다 다를 수 있다. 추가 레이어가 있으면 이 표에 그 책임·허용 의존을 추가하고, 아래 방향 규칙을 그에 맞춰 확장한다. 실제 레포 레이어는 `Packages/` 디렉토리 구성과 각 `Package.swift`의 `dependencies` 배열로 확인한다.

## 허용 의존 방향

### 1. 단방향 (상위 → 하위만)

```
App ──→ (전부)
Feature ──→ Domain, DesignSystem
Data ──→ Domain, Networking
DesignSystem ──→ Core
Domain ──→ Core
Networking ──→ Core
Core ──→ (없음)
```

- 각 모듈은 위 표의 허용 의존만 가진다.
- **하위는 상위를 의존하지 않는다.** Domain → Feature, Core → Domain 같은 역방향은 모두 금지.

### 2. 수평 의존 금지

- 같은 레이어 모듈끼리 직접 의존하지 않는다. `Feature ↛ Feature`.
- 공유가 필요하면 공유 부분을 **하위 레이어로 내려** 거기서 의존한다. 예: 두 Feature가 같은 모델을 쓰면 그 모델을 Domain(또는 Core)에 두고 각 Feature가 그것을 의존한다.

### 3. 사이클 금지

- 어떤 경로로도 의존이 자기 자신으로 돌아오지 않는다. A → B → A, A → B → C → A 모두 금지.

## DDD 경계 규칙

레이어 방향 위에 DDD 책임 경계가 겹친다.

- **Repository protocol = Domain, 구현 = Data.** Domain은 인터페이스만 소유하고, `Default*` 구현은 Data가 가진다. Feature는 Domain의 protocol에만 의존한다.
- **DTO는 Data internal.** DTO를 Domain으로 노출하거나 Domain 타입으로 흘려보내지 않는다. Data가 경계에서 DTO ↔ Entity 변환을 책임진다.
- **Entity는 Codable을 직접 준수하지 않는다.** 직렬화 형태는 Data의 DTO가 진다. Entity에 `Codable`을 붙이는 순간 도메인이 전송 포맷에 묶인다.
- **인프라 오류는 Data에서 번역한다.** `NetworkError` 등 인프라 오류를 Data 경계에서 `DomainError`로 옮겨 던진다. 상위 레이어는 `DomainError`만 다룬다.

## 경계 판정 — 모듈을 어디에 둘까

새 모듈·분리 대상을 배치할 때:

1. **하는 일 한 줄**을 적는다.
2. "화면·사용자 흐름이 보이는가?" → 보이면 Feature.
3. "Repository 구현·DTO·인프라 연동인가?" → Data.
4. "화면 없이 도메인 규칙·엔티티만 다루는가?" → Domain.
5. "전송 추상인가 / 공용 UI인가?" → Networking / DesignSystem.
6. "레이어와 무관하게 어디서나 쓰일 기반인가?" → Core.
7. 애매하면 **더 하위(더 의존받는) 레이어로 내리는 쪽**을 우선 검토한다 — 상위는 교체가 싸고, 하위로 잘못 내린 것은 의존자가 생긴 뒤 되돌리기 비싸다.

## 흔한 위반과 교정

| 위반 | 증상 | 교정 |
|---|---|---|
| 역방향 | Domain이 Feature를 import | 끌어쓰던 타입을 Domain/Core로 내리고 의존 뒤집기 |
| 수평 | FeatureA가 FeatureB를 import | 공유 부분을 Domain/Core로 추출해 양쪽이 그것을 의존 |
| DTO 누출 | Domain·Feature가 DTO를 직접 다룸 | DTO를 Data internal로 가두고 경계에서 Entity로 변환 |
| 오류 누출 | 상위 레이어가 `NetworkError`를 catch | Data 경계에서 `DomainError`로 번역해 던지기 |
| Core 비대 | Core가 특정 Feature 전용 로직을 가짐 | 그 로직을 해당 Domain/Feature로 올림 |
| 우회 사이클 | A→B→C→A 형태 | 사이클을 끊는 추상(인터페이스)을 하위 레이어에 두고 의존 역전 |

## 빌드가 못 잡는다는 점

위 방향 규칙은 **모두 `dependencies`에 선언하면 컴파일러를 통과한다.** 역방향·수평 의존을 `Package.swift`의 `dependencies`에 적으면 빌드는 초록불이 된다. (미선언 모듈 import는 SPM이 컴파일 실패로 잡지만, 선언된 역방향은 못 잡는다.) 그래서 방향 준수는 빌드가 아니라 [deps-verify.md](deps-verify.md)의 track B(`Package.swift`의 `dependencies` 배열을 레이어 규칙과 대조)로 검증한다.
