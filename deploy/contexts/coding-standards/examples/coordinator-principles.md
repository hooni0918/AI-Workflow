# 파일: deploy/contexts/coding-standards/examples/coordinator-principles.md

> **예시 (참고용).** Coordinator 패턴을 쓰는 프로젝트의 예시다. 마스터 표준이 아니며, 네 프로젝트의 .claude/docs에 네 것으로 정의해 대체하라.

# Coordinator 아키텍처 원칙 (예시)

화면 전환의 책임을 `View`에서 분리해 Coordinator에 모으는 이유와 그 경계 판단을 다룬 예시다. 기계 대조 가능한 "~해라/~금지"(예: 네비게이션 의존 방향 규칙)는 네 프로젝트의 `.claude/docs`가 단일 출처다 — 여기서는 *왜* 그렇게 가르는지(판단 근거)만 예시로 보인다.

## 왜 전환을 View에서 떼어내는가

`View`가 "다음에 어느 화면으로 갈지"를 직접 알면 세 가지가 따라온다.

- **재사용 불가**: 같은 `View`를 다른 플로우에서 재사용하려 해도, 박혀 있는 다음 화면 때문에 그대로 못 쓴다.
- **테스트 곤란**: 전환 분기(로그인 여부에 따라 다른 화면 등)가 `View` 안에 있으면, 그 분기를 검증하려면 `View`를 띄워야 한다. 전환 로직이 Coordinator에 있으면 Coordinator만 단위 테스트할 수 있다.
- **흐름 파악 곤란**: 화면 전환의 전체 그림이 여러 `View`에 흩어져, 플로우를 한눈에 볼 곳이 없다.

Coordinator는 "이 플로우에서 화면들이 어떤 순서·조건으로 이어지는가"를 한 곳에 모은다. `View`는 "사용자가 무엇을 했다"는 의도만 올린다.

## 의존 방향의 비대칭이 핵심

`View → Coordinator`는 허용, `Coordinator → 구체 View`는 금지다. 이 비대칭이 깨지면 — Coordinator가 화면마다 구체 `View`를 알면 — Coordinator가 모든 화면의 허브가 되어 화면이 늘 때마다 비대해지고, 모듈로 쪼갤 때 Feature 모듈끼리 Coordinator를 통해 간접 결합된다. Coordinator는 **Route라는 추상**까지만 알고, Route를 실제 `View`로 만드는 책임은 팩토리 한 곳에 둔다.

> 이 의존 방향 결함은 "Coordinator는 구체 View를 몰라야 한다"는 규칙을 알아야 보인다. 코드만 보면 평범한 `import`로 보이므로, 리뷰·인계에서 지적할 때는 위배된 규칙(의존 방향)을 함께 명시한다. 그 규칙의 정확한 형태는 네 프로젝트의 `.claude/docs`가 단일 출처다.

## 어디까지가 Coordinator의 일인가

- **Coordinator의 일**: 화면 전환(push/present/dismiss/탭 전환), 플로우 분기(조건에 따라 다음 화면 결정), 딥링크 Route 해석 후 같은 경로로 흘리기.
- **Coordinator의 일이 아닌 것**: 화면 내부 상태·검증·데이터 로딩(화면 상태 객체의 일), 마크업(`View`의 일).

전환과 무관한 비즈니스 로직을 "어디 둘지 애매해서" Coordinator에 넣지 않는다. Coordinator가 비즈니스 로직을 떠안으면 다시 거대한 만능 객체가 되어, 전환을 떼어낸 처음의 목적이 무너진다.
