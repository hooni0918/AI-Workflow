# coding-standards

## 역할

iOS 코딩 표준을 **정의·강제하는 방법**의 마스터 인덱스다. 구체적인 아키텍처(Clean Arch/DDD 등)·UI 프레임워크(UIKit/SwiftUI 등)·레이어 목록·네이밍 접미사는 **고르지 않는다**. 그 구체 사실은 **사용 레포가 공급**한다 — 사용 레포의 `.claude/docs/architecture.md`, `layer-rules.json`, `.claude/docs/project-profile.md`.

마스터는 두 종류로 구성된다:

- **rules** (`rules/`): "~해라, ~금지" 형태의 텍스트 규칙. AI가 코드를 대조할 때 참조한다. 중간 모델(예: sonnet)도 기계적으로 대조 가능한 수준으로 적는다.
- **principles** (`principles/`): 응집도·결합도·아키텍처 경계처럼 판단이 필요한 기준. 최상위 모델(예: opus) 판단을 전제한다.

같은 주제라도 역할이 다르므로 양쪽에 공존할 수 있다.

이 마스터의 규칙·원칙은 *스택을 고정하지 않는 범용 규율*(예: Swift 언어 규칙, 네이밍 규율, SPM 모듈화 방법론, 아키텍처 경계 원칙)과 *그것을 강제하는 방법*만 담는다. 특정 스택에서 그 규율을 어떻게 적었는지 보고 싶으면 [examples/](examples/README.md)를 참고하되, 그것은 예시이지 마스터 규칙이 아니다.

### 프로젝트 config에 위임

구체 사실은 마스터가 정하지 않고 프로젝트가 공급한다. 마스터 규칙은 다음 순서로 출처를 따른다:

1. 프로젝트에 해당 config가 있으면 **그것이 1차 출처**다. 마스터 본문과 어긋나면 프로젝트 config를 따른다.
   - 아키텍처·레이어·경계: `.claude/docs/architecture.md`
   - 레이어 목록·허용 의존 방향(기계 대조용): `layer-rules.json`
   - 채택 스택(아키텍처·UI 프레임워크·네이밍 규약 등) 요약: `.claude/docs/project-profile.md`
2. config가 없거나 침묵하면, 사용자에게 묻거나 안전 가정으로 진행하되 **"(가정)" 라벨**을 유지한다.

기술 사실(SPM dependencies 레이어 대조, stub 검증 한계, `@Observable` 도입 조건, Swift 6 strict concurrency 강제 조건)은 이 디렉토리가 단일 출처가 아니다. [testing-strategy/assumptions.md](../testing-strategy/assumptions.md)가 단일 출처이고, 이 디렉토리의 규칙이 그 사실에 기대면 본문 재기술 대신 그 파일을 가리킨다.

## 로드 규칙

- 회사(실무) 프로젝트: `universal/` 만
- 개인 프로젝트: `universal/` + `personal/`

`universal/`은 팀원 누구나 동의할 범용 규칙, `personal/`은 작성자 개인이 더 세밀하게 적용하는 기준이다.

### 탐색 절차

1. 이 문서 하단의 rules·principles 파일 리스트를 훑고, 현재 작업과 관련된 파일을 선별한다.
2. 작업 대상 프로젝트의 구체 사실(아키텍처·레이어·네이밍)이 필요하면, 먼저 그 프로젝트의 `.claude/docs/architecture.md`·`layer-rules.json`·`.claude/docs/project-profile.md`를 1차 출처로 확인한다. 없으면 사용자에게 묻거나 안전 가정으로 진행한다(가정 라벨 유지).
3. 리뷰·구현 대상이 기존 코드베이스 위에서 도는 작업이면, 같은 역할을 하는 기존 패턴을 코드베이스에서 직접 탐색해 참조한다 — 같은 것을 두 번 설계하지 않기 위함이다.
4. 선별한 파일을 모두 Read한다. 파일명만 보고 판단하지 않는다.
5. 매칭되는 규칙·패턴이 있으면 그 기준을 엄격하게 따른다. 프로젝트 상황과 맞지 않아 판단이 어려운 부분은 임의로 변형하지 않고 사용자에게 확인한다.

## 정적분석 사다리

코드 컨벤션은 강제 메커니즘이 강한 순서로 시도한다 — **정적분석 → hook → 프롬프트 규칙**. 정적분석은 사람·CI·다른 도구 어디서나 걸리고, hook은 에이전트 런타임 안에서만 발동하기 때문이다. 마스터는 강제 *방법*을 제공하고, 그 안에 들어갈 *값*(룰 임계치·레이어 목록)은 프로젝트가 채운다.

- **SwiftLint** — 마스터 [swiftlint 템플릿](../../templates/swiftlint.template.yml)에 베이스 설정 템플릿을 둔다. 프로젝트는 이를 복사해 자기 규칙으로 조정한다. 강제 unwrap·force-try 금지, 접근제어 명시 등 스타일·언어 규칙을 기계 대조한다.
- **레이어 의존 대조** — `check_spm_layers.py`가 각 `Packages/<M>/Package.swift`의 `dependencies` 배열을 떠서 허용 방향과 대조한다. 허용 방향(레이어 목록·의존표)은 마스터가 정하지 않고 프로젝트의 `layer-rules.json`(없으면 `.claude/docs/architecture.md`)이 공급한다. "빌드 성공 ≠ 레이어 규칙 준수"의 간극을 결정론적으로 메운다.
- **hook** — 위 정적분석으로 못 거는, 또는 에이전트 런타임에서 추가로 강제하고 싶은 항목만 hook으로 올린다.

각 규칙 파일 본문에서 기계 대조 가능한 항목은 어느 도구(SwiftLint 룰 ID·`check_spm_layers.py`)로 강제하는지 명시한다.

## 태그

| 태그 | 의미 | 사용 시점 |
|------|------|-----------|
| `file-folder-structure` | 파일·폴더 분리, 모듈 경계 기준 | 구현 구조·모듈 설계 시 |

## rules (중간 모델 이상 대조 가능, e.g. sonnet)

범용 규율만 둔다. 특정 UI 프레임워크·아키텍처를 고르지 않는다.

rules/universal/swift/general.md
rules/naming.md
rules/spm-modularization.md [file-folder-structure]

## principles (최상위 모델 판단 필요, e.g. opus)

범용 아키텍처 경계·품질 원칙만 둔다. 구체 아키텍처 선택은 프로젝트가 공급한다.

principles/architecture.md

## examples (프로젝트가 대체하는 예시)

특정 스택(예: Clean Arch/DDD·UIKit/SwiftUI·구체 레이어·네이밍 접미사)에서 위 규율을 *어떻게 적었는지* 보여주는 참고 모음이다. **마스터 규칙으로 인용하지 않는다.** 네 프로젝트의 `.claude/docs/architecture.md`·`layer-rules.json`·`.claude/docs/project-profile.md`에 네 것으로 정의해 대체한다. 목록은 [examples/README.md](examples/README.md) 참고.

## templates (마스터가 제공하는 강제 도구)

프로젝트가 복사해 자기 값으로 채우는 강제 도구 템플릿은 마스터 `templates/`에 둔다.

[swiftlint 템플릿](../../templates/swiftlint.template.yml) — SwiftLint 베이스 설정 템플릿
