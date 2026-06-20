# PLAN — 레이어 설계 + Package.swift 작성

SKILL.md 「작업 진행 순서」의 PLAN 세션 본문이다. **코드 본체를 만들지 않는다.** 레이어 의존을 설계하고 `Package.swift` 변경안을 작성한 뒤, 사용자 승인을 받아 APPLY로 넘긴다.

진입 시 SKILL.md 「[CRITICAL] 지킬 원칙」과 [conventions/module-layers.md](conventions/module-layers.md)를 먼저 읽는다.

## 0. 현재 레이어 파악

작업 전 현재 의존 위상을 확인한다. 기억이 아니라 파일 내용으로 시작한다.

```bash
grep -nE '\.package\(path:' Packages/*/Package.swift
```

- 각 로컬 패키지의 `Package.swift` `dependencies` 배열을 읽어 **현재 모듈 목록과 의존 방향**을 파악한다. SPM에는 그래프 산출 명령이 없으므로 의존 위상은 이 배열들의 합집합이다.
- 레이어 목록·경계의 **1차 출처**는 프로젝트의 `layer-rules.json`·`architecture.md`(경로는 project-profile.md가 가리킨다)다 — 거기 정의된 레이어·허용 방향을 따른다. 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행한다. 이 step은 방법론(레이어 단방향·수평 금지·사이클 금지)을 담고, 프로젝트 고유의 정확한 경계는 그 문서에 위임한다.
- 대상 모듈이 이미 있으면(재구성), 그 모듈이 현재 무엇을 의존하고 무엇에게 의존받는지(in/out edge)를 적는다.
- 이 출력은 PLAN의 입력이자 APPLY 검증의 "before" 기준이 된다.

## 1. 작업 분류

사용자 요구를 다음 중 하나로 분류하고, 분류 결과를 설계서에 적는다.

- **추가**: 새 모듈(로컬 패키지)을 의존 그래프에 넣는다.
- **분리**: 한 모듈을 둘 이상으로 쪼갠다 (예: 비대한 상위 모듈에서 순수 도메인 규칙을, 공용 기반을 더 하위 레이어로).
- **병합**: 둘 이상을 합친다.
- **의존 재배치**: 모듈은 그대로 두고 의존 방향·경로만 바꾼다 (예: 같은 레이어 간 직접 의존을 하위 레이어 경유로 교정).

## 2. 레이어 배치 판정

각 대상 모듈을 어느 레이어에 둘지 판정한다. 기준은 [conventions/module-layers.md](conventions/module-layers.md)의 레이어 정의·책임(방법론)이며, **실제 레이어 목록·경계는 프로젝트의 `layer-rules.json`·`architecture.md`가 1차 출처**다(경로는 project-profile.md). 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행한다.

판정 절차:

1. 모듈이 **하는 일**을 한 줄로 적는다.
2. 프로젝트가 정의한 레이어의 책임과 대조해 배치한다. 책임 → 레이어 매핑의 흔한 형태(예시 — 실제 레이어명은 프로젝트가 정의):
   - 화면·사용자 흐름 → 상위 UI 레이어 (예: Feature)
   - 화면과 무관한 도메인 규칙·엔티티·값객체·UseCase/Repository 프로토콜 → 도메인 레이어 (예: Domain)
   - Repository 구현·원격 통신·DTO 매핑 → 데이터 레이어 (예: Data)
   - 네트워킹 추상·전송 계층 → 전송 레이어 (예: Networking)
   - 디자인 토큰·공용 UI 컴포넌트 → 공용 UI 레이어 (예: DesignSystem)
   - 레이어 무관 공용 기반(확장·유틸·로깅 등) → 최하위 공용 레이어 (예: Core)
3. 배치가 애매하면 **더 낮은(더 의존받는) 레이어로 내리는 쪽**을 우선 검토한다. 상위 레이어는 갈아끼우기 쉽지만, 하위로 내린 것을 다시 올리려면 의존자가 깨진다.

## 3. 의존 방향 설계

각 모듈이 **무엇을 의존할지**를 방향과 함께 적는다. 허용 방향의 방법론 출처는 [conventions/module-layers.md](conventions/module-layers.md)이고, **실제 레이어 목록·허용 방향은 프로젝트의 `layer-rules.json`·`architecture.md`가 1차 출처**다(경로는 project-profile.md). 없으면 사용자에게 묻거나 안전 가정(가정 라벨)으로 진행한다.

검사 항목 (위반이면 설계를 고친다):

- **단방향**: 의존은 상위 → 하위로만 흐른다 (예: Feature → Domain → Core). 역방향(하위가 상위 의존)은 금지.
- **수평 금지**: 같은 레이어끼리 직접 의존하지 않는다 (예: FeatureA ↛ FeatureB). 공유가 필요하면 공통 부분을 하위 레이어로 내려 거기서 의존한다.
- **사이클 금지**: 어떤 경로로도 의존이 자기 자신으로 돌아오지 않는다.

설계 결과를 텍스트 그래프로 적는다 (예시 — 실제 레이어는 프로젝트 `layer-rules.json`/`architecture.md`):

```
Feature ──→ Domain ──→ Core
        └─→ DesignSystem ──→ Core
Data ──→ Domain
     └─→ Networking ──→ Core
```

## 4. Package.swift 변경안 작성

위 설계를 각 로컬 패키지의 `Package.swift`에 옮긴다. **변경안(diff 형태)만 작성**하고 파일에 반영하지 않는다 — 반영은 APPLY가 한다.

- 새 패키지면 레포의 동일 패턴을 미러링한다: `product`는 패키지명 단일 `.library`, `target` + `testTarget`(이름=패키지명), swift-tools·platforms·swiftLanguageModes를 형제 패키지와 맞춘다. (정확한 값은 기존 `Package.swift`를 인덱스로 확인)
- 의존은 **3단계에서 설계한 방향만** 로컬 경로 의존(`.package(path: "../X")` + 타깃 `dependencies`)으로 적는다. "일단 다 넣고 나중에 뺀다"는 금지 — 선언한 의존은 빌드를 통과시키므로 과잉 선언이 곧 그래프 오염이다. 특히 SPM은 `dependencies`에 역방향을 적어도 컴파일이 통과하므로, 배열에 적는 것 자체가 그래프 결정이다.
- **App 링크 계획 (모듈 시스템이 SPM + 별도 App 프로젝트인 경우)**: 프로젝트가 SPM 로컬 패키지와 별도 App 프로젝트(예: `App.xcodeproj`)로 구성된 경우, 새 모듈이 앱에서 직접 쓰여야 하면 App 타깃이 그 로컬 패키지 라이브러리를 링크하도록 하는 변경을 설계서에 적는다 (App은 컴포지션 루트로서 전 모듈을 의존). App 타깃에 직접 링크할지, 상위 패키지를 경유해 transitive로 끌어올지 방향 규칙에 맞춰 정한다 — 반영 절차는 APPLY가 수행한다. 모듈 시스템·App 구성은 project-profile.md가 1차 출처이며, 단일 타깃 등 별도 App 프로젝트가 없는 구성이면 이 step은 건너뛴다.

## 5. 설계서 정리 + 승인

다음을 담은 설계서를 정리해 사용자에게 제시하고 승인을 받는다.

- 작업 분류 (1단계)
- 모듈별 레이어 배치와 근거 (2단계)
- 의존 방향 텍스트 그래프 (3단계)
- `Package.swift` 변경안 diff + (해당 시) App 링크 계획 (4단계)
- **가정 라벨**: 대상 모듈의 테스트 러너·시뮬레이터 식별자, 화면 상태 패턴(전용 패턴 미정) 등 미확인 항목 (SKILL.md 「미확정은 "가정" 라벨」). 테스트 명령·빌드 명령·UI 프레임워크·언어/플랫폼 설정의 1차 출처는 project-profile.md이며, 거기에 확정값이 있으면 가정이 아니라 사실로 적는다.

사용자가 명시적으로 "계획 먼저 보여줘" 흐름을 원하면 plan mode로 제시한다.

## 6. 종료 — APPLY spawn 안내

승인 후, SKILL.md 「세션」 표를 참조해 후속 안내를 출력한다.

- `/spm-module APPLY <동일 작업 대상 인자>` 로 적용 세션을 spawn하도록 안내한다.
- 표 (권장 모델) 칸도 함께 안내한다 (PLAN이 레이어·`Package.swift`를 확정했으면 Sonnet, 미해결 설계 판단을 남겼으면 Opus).
- 설계서·`Package.swift` 변경안이 APPLY의 입력임을 명시한다. 단, APPLY의 **검증 기준은 설계서가 아니라** 레이어 규칙 1차 출처(프로젝트 `layer-rules.json`/`architecture.md`, 없으면 방법론으로 [conventions/module-layers.md](conventions/module-layers.md))와 각 `Package.swift`의 `dependencies` 배열·빌드 출력임을 함께 안내한다 (자기증명 차단).

출력 직후 "이 세션은 종료되었습니다" 한 줄로 마무리한다.
