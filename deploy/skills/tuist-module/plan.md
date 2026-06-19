# PLAN — 그래프 설계 + manifest 작성

SKILL.md 「작업 진행 순서」의 PLAN 세션 본문이다. **코드 본체를 만들지 않는다.** 그래프를 설계하고 Tuist manifest 변경안을 작성한 뒤, 사용자 승인을 받아 APPLY로 넘긴다.

진입 시 SKILL.md 「[CRITICAL] 지킬 원칙」과 [conventions/module-layers.md](conventions/module-layers.md)를 먼저 읽는다.

## 0. 현재 그래프 파악

작업 전 현재 의존 위상을 확인한다. 기억이 아니라 도구 출력으로 시작한다.

```bash
tuist graph
```

- 출력(그래프 파일·DOT·이미지 등 Tuist 버전이 산출하는 형식)을 읽어 **현재 모듈 목록과 의존 방향**을 파악한다. (가정: Tuist 4.x)
- 대상 모듈이 이미 있으면(재구성), 그 모듈이 현재 무엇을 의존하고 무엇에게 의존받는지(in/out edge)를 적는다.
- 이 출력은 PLAN의 입력이자 APPLY 검증의 "before" 기준이 된다.

## 1. 작업 분류

사용자 요구를 다음 중 하나로 분류하고, 분류 결과를 설계서에 적는다.

- **추가**: 새 모듈을 그래프에 넣는다.
- **분리**: 한 모듈을 둘 이상으로 쪼갠다 (예: 비대한 Feature에서 순수 로직을 Domain으로, 공용 유틸을 Core로).
- **병합**: 둘 이상을 합친다.
- **의존 재배치**: 모듈은 그대로 두고 의존 방향·경로만 바꾼다 (예: Feature 간 직접 의존을 Domain 경유로 교정).

## 2. 레이어 배치 판정

각 대상 모듈을 어느 레이어에 둘지 판정한다. 기준은 [conventions/module-layers.md](conventions/module-layers.md)의 레이어 정의·책임이다.

판정 절차:

1. 모듈이 **하는 일**을 한 줄로 적는다.
2. [conventions/module-layers.md](conventions/module-layers.md)의 각 레이어 책임과 대조해 배치한다.
   - 화면·사용자 흐름·화면 상태 → Feature
   - 화면과 무관한 도메인 규칙·엔티티·유스케이스 → Domain
   - 레이어 무관 공용(네트워킹·디자인 토큰·확장·로깅 등) → Core
3. 배치가 애매하면 **더 낮은(더 의존받는) 레이어로 내리는 쪽**을 우선 검토한다. 상위 레이어는 갈아끼우기 쉽지만, 하위로 내린 것을 다시 올리려면 의존자가 깨진다.

## 3. 의존 방향 설계

각 모듈이 **무엇을 의존할지**를 방향과 함께 적는다. 허용 방향의 단일 출처는 [conventions/module-layers.md](conventions/module-layers.md)다.

검사 항목 (위반이면 설계를 고친다):

- **단방향**: 의존은 상위 → 하위로만 흐른다 (Feature → Domain → Core). 역방향(하위가 상위 의존)은 금지.
- **수평 금지**: 같은 레이어끼리 직접 의존하지 않는다 (FeatureA ↛ FeatureB). 공유가 필요하면 공통 부분을 하위 레이어로 내려 거기서 의존한다.
- **사이클 금지**: 어떤 경로로도 의존이 자기 자신으로 돌아오지 않는다.

설계 결과를 텍스트 그래프로 적는다 (예):

```
SearchFeature ──→ SearchDomain ──→ NetworkCore
              └─→ DesignCore
```

## 4. manifest 변경안 작성

위 설계를 Tuist manifest(`Project.swift` 또는 워크스페이스 manifest. 레포 구조에 맞춰 확인)에 옮긴다. **변경안(diff 형태)만 작성**하고 파일에 반영하지 않는다 — 반영은 APPLY가 한다.

- 새 타겟 정의·`dependencies` 배열·product 타입(framework/staticFramework/library 등)을 적는다.
- 의존은 **3단계에서 설계한 방향만** 적는다. "일단 다 넣고 나중에 뺀다"는 금지 — 선언한 의존은 빌드를 통과시키므로 과잉 선언이 곧 그래프 오염이다.
- manifest 표현이 레포의 헬퍼(ProjectDescriptionHelpers 등)에 의존하면 그 헬퍼 경로·시그니처를 설계서에 인덱스로 남긴다 (APPLY가 빠르게 찾도록).

## 5. 설계서 정리 + 승인

다음을 담은 설계서를 정리해 사용자에게 제시하고 승인을 받는다.

- 작업 분류 (1단계)
- 모듈별 레이어 배치와 근거 (2단계)
- 의존 방향 텍스트 그래프 (3단계)
- manifest 변경안 diff (4단계)
- **가정 라벨**: Tuist 버전, deployment target(`@Observable`·iOS 17+ 관련), strict concurrency mode, 테스트/스냅샷 존재 여부 등 미확인 항목 (SKILL.md 「미확정은 "가정" 라벨」)

사용자가 명시적으로 "계획 먼저 보여줘" 흐름을 원하면 plan mode로 제시한다.

## 6. 종료 — APPLY spawn 안내

승인 후, SKILL.md 「세션」 표를 참조해 후속 안내를 출력한다.

- `/tuist-module APPLY <동일 작업 대상 인자>` 로 적용 세션을 spawn하도록 안내한다.
- 표 (권장 모델) 칸도 함께 안내한다 (PLAN이 그래프·manifest를 확정했으면 Sonnet, 미해결 설계 판단을 남겼으면 Opus).
- 설계서·manifest 변경안이 APPLY의 입력임을 명시한다. 단, APPLY의 **검증 기준은 설계서가 아니라** [conventions/module-layers.md](conventions/module-layers.md)와 `tuist graph` 출력임을 함께 안내한다 (자기증명 차단).

출력 직후 "이 세션은 종료되었습니다" 한 줄로 마무리한다.
