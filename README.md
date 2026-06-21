# AI Workflow

AI 시대 개발자의 가치는 두 가지라고 생각합니다. **일을 AI에게 잘 시키는 것**, 그리고 **AI가 만든 결과물을 잘 리뷰하는 것**.

이 스킬은 전자를 위해 만들었습니다.

## 한 번 내린 판단을 프롬프트로

한 번 내린 판단은 프롬프트로 만들어 AI에게 위임합니다. 같은 결정을 두 번 하지 않기 위해서입니다.

### 일하는 방식을 옮긴 워크플로우

 [ios-workflow](deploy/skills/ios-workflow/README.md)는 제가 앱을 만드는 방식을 그대로 프롬프트로 옮긴 것입니다. 기획서나 디자인 시안을 넣으면 PR이 나옵니다. 피그마도 그런 입력 자료의 하나일 뿐이라, 별도 연동 도구 없이 사용자가 준 URL이나 캡처를 그대로 읽습니다.

작업은 여러 단계로 나뉘어 각각 독립된 맥락에서 진행됩니다. 자료를 읽고 무엇을 왜 해야 하는지 정리한 뒤 할 일을 PR 단위로 쪼개고, 화면을 프로젝트가 쓰는 UI 프레임워크로 마크업하는 작업을 PR 작업과 동시에 만들고, PR마다 설계와 구현, 본문 작성을 거칩니다. 설계 단계에서는 프로젝트가 정한 아키텍처 레이어의 경계를 먼저 긋고, 새 모듈이나 의존성이 필요하면 모듈 구성을 함께 정합니다.

다음 PR의 설계를 이번 PR 구현과 겹쳐 돌리기 때문에 여러 PR이 병렬로 흐릅니다.

### 회고를 옮긴 마무리 절차

[pre-exit](deploy/skills/pre-exit/README.md)는 세션이 끝날 때 회고를 수행하는 스킬입니다. 그 회고를 통해 스킬 자체도 개선합니다. 회고하는 방법 자체도 프롬프트가 된 셈입니다.

반복된 실수 패턴을 찾아 규칙으로 남길 자리를 제안하고, 거기서 얻은 교훈을 그 교훈이 쓰일 자리에 직접 심어 둡니다. 사람이 기억하지 않아도 AI가 해당 맥락에서 자동으로 꺼내 씁니다.

## AI가 먼저 제안합니다

미리 방향을 정해두면, AI가 그 안에서 사용자가 미처 보지 못한 것을 발굴합니다.

[ios-workflow](deploy/skills/ios-workflow/README.md)의 요구사항 리뷰 단계(step-1.2)는 기획서, 디자인 시안, 채용 과제를 구현 전에 iOS 개발자 관점에서 점검합니다. 기획서는 화면 목적과 사용자 동선, 예외 상황을 짚고, 디자인 시안은 다양한 기기 크기와 다크 모드, 로딩·빈·에러 같은 상태별 화면을 살피고, 채용 과제는 숨은 평가 포인트를 역으로 추론합니다. 화면 종류(리스트·상세·폼·순차 플로우)별 체크리스트는 [requirement-review/screen-type](deploy/skills/ios-workflow/requirement-review/screen-type/)에 있습니다.

요구사항을 받자마자 코드를 짜면 빈틈이 구현 도중에야 드러납니다. 그 빈틈을 먼저 질문으로 끄집어내 두는 것이 이 스킬의 일입니다.

## 리뷰 비용을 줄이는 구조

AI가 짜는 코드가 늘면 사람이 봐야 할 양도 같이 늘어납니다. 답은 리뷰를 더 열심히 하는 게 아니라 볼 양 자체를 줄이는 겁니다.

도입 비용이 싼 것부터 보겠습니다.

### 자동 검사로 거르기

동작은 하지만 버그를 품은 패턴이 있습니다. 사람이 수백 줄을 읽으며 매번 찾아내기는 어렵습니다. 이런 패턴은 가능한 한 컴파일·정적 분석 단계에서 차단해, 리뷰어가 로직과 설계에만 집중하도록 만듭니다.

다만 어디까지 자동으로 잡히는지를 정확히 알고 써야 합니다.

- **타입 시그니처는 컴파일러가 보증합니다.** stub(빈 구현)을 먼저 깔고 시그니처 정합만 맞춰 두면 호출부와의 타입 어긋남은 컴파일이 막아 줍니다. 하지만 미구현 누락(본문이 비어 있는 함수)은 컴파일러가 잡지 못합니다. 특히 저장 프로퍼티 초기값처럼 값이 반드시 있어야 하는 자리는 `fatalError`로 메울 수 없으므로, 빈 채로 두면 컴파일은 통과해도 런타임에서야 드러납니다.
- **레이어 경계는 SPM 의존성으로 검사합니다.** 선언하지 않은 import는 SPM 컴파일이 막습니다(`Package.swift`의 `dependencies`에 없는 모듈을 import하면 빌드 실패). 모듈 사이의 역방향 의존(단방향이어야 할 의존이 뒤집힌 경우)은 각 `Package.swift`의 `dependencies` 배열을 레이어 규칙과 대조해 잡습니다. 둘은 잡는 대상이 다르므로 구분해서 씁니다.
- **동시성·관찰 모델은 프로젝트 설정에 달렸습니다.** strict concurrency가 컴파일러 강제로 걸리는지(모듈이 strict mode인지), `@Observable` 같은 API가 가용한지(배포 타깃)는 프로젝트 프로필·architecture.md가 1차 출처입니다. 강제 모드가 켜져 있으면 데이터 경합 위반이 빌드 게이트로 잡히고, 미공급이면 가정으로 두고 단정하지 않습니다.

### 테스트로 거르기

AI가 코드를 만들거나 고칠 때마다, 기존 동작이 깨지지 않았는지 테스트가 자동으로 확인합니다. 사람이 직접 검증해야 할 범위가 그만큼 줄어듭니다.

빌드는 `xcodebuild`로 App 스킴을 돌리고, 테스트는 패키지별로 `swift test`(순수 로직 패키지) 또는 `xcodebuild test`(시뮬레이터가 필요한 패키지)로 돌립니다. 정확한 명령은 [conventions/spm.md](deploy/skills/ios-workflow/conventions/spm.md)가 단일 출처입니다.

스냅샷 테스트는 단계에 따라 역할이 다릅니다. 검증 단계에서는 오라클로 동작해, 기준 이미지와 diff가 나면 실패로 떨어집니다. 사람이 개입하는 것은 기준 이미지를 새로 박는 record 단계뿐입니다. (가정: 스냅샷·CI 구성은 프로젝트별로 확정 필요.)

### AI 리뷰로 거르기

자동 검사가 잡지 못하는 문제(화면과 데이터 로직이 섞여 분리가 필요한 경우, 화면이 비즈니스 로직을 직접 구현해 레이어 경계를 어긴 경우 등)는 AI 리뷰가 맡습니다. 반복된 지적은 [coding-standards](deploy/contexts/coding-standards/README.md)에 규칙으로 쌓아 두고 [code-review](deploy/skills/code-review/README.md) 스킬이 그 규칙을 읽어 대조하므로, 사람이 리뷰에 쓰는 시간이 점점 줄어듭니다.

## 배포

스킬과 규칙, hook은 `make`로 배포합니다. 배포 인프라는 Python(`python3 scripts/*.py`)으로 짰고, 진입점은 `Makefile`입니다.

```sh
make sync-system        # 전역 배포 (~/.claude, ~/.codex, ~/.gemini)
make install-hooks      # .git/hooks/commit-msg 에 커밋 메시지 검사 hook 연결
make verify-hooks       # hook이 올바르게 연결됐는지 확인
```

전체 타겟 목록은 `Makefile`을 참고하세요.

## 스킬 목록

### 개발 워크플로우

- [ios-workflow](deploy/skills/ios-workflow/README.md): 기획서나 디자인 시안 같은 입력 자료를 넣으면 PR이 나오는 단계별 프로세스
  - 요구사항 리뷰(step-1.2): 자료를 구현 전에 iOS 개발자 관점에서 점검합니다. 화면 종류별 체크리스트는 [requirement-review/screen-type](deploy/skills/ios-workflow/requirement-review/screen-type/)에 있습니다

### 모듈 구성

- [spm-module](deploy/skills/spm-module/README.md): 새 화면·기능에 맞춰 SPM 로컬 패키지를 추가하고 의존 그래프를 단방향으로 유지

### 리뷰

- [code-review](deploy/skills/code-review/README.md): 코드 변경을 [coding-standards](deploy/contexts/coding-standards/README.md)와 품질 기준으로 리뷰하고 고칠 거리 목록 산출

### 커뮤니케이션

- [discussion](deploy/skills/discussion/README.md): 기술 주제에 대해 비판적으로 토론

### 유틸리티

- [pre-exit](deploy/skills/pre-exit/README.md): 세션 종료 시 회고 및 스킬 개선
