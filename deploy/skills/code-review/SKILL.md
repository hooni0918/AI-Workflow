---
name: code-review
description: 코드 변경사항을 리뷰하고 이슈 목록을 산출한다. 코드리뷰, PR 리뷰, 코드 점검 요청 시 사용.
argument-hint: "[PR URL 또는 브랜치] [--coding-standards 경로...] [--extra-standards 경로...] [--mode default|advanced|only-standards]"
---

# Code Review

## 목적

코드 변경사항을 검증하고 이슈 목록을 산출한다.

**수정은 하지 않는다** — 이슈 목록만 반환하고, 수정 여부와 방법은 호출자가 결정한다.

## 입력

| 입력 | 필수 | 설명 |
|------|------|------|
| **리뷰 대상** | O | PR diff, 커밋, 파일 |
| **coding-standards 목록** | X | 적용할 coding-standards 파일 경로 리스트. 없으면 [map.md](../../contexts/coding-standards/map.md)에서 직접 판단 |
| **추가 컨벤션** | X | coding-standards 외 경로 (사내 컨벤션 등) |
| **리뷰 모드** | X | default / advanced / only-standards (기본: default) |

## 출력

이슈 목록. severity (Critical / Minor / Suggestion) 포함.

- **advanced 모드에서 coding-standards 이슈가 있으면**: coding-standards 이슈만 반환하고 "coding-standards 미통과로 advanced 미실행" 안내. 호출자가 수정 후 재호출하면 다시 판단한다.

---

## 절차

### 1. 컨텍스트 준비

coding-standards 목록이 주입된 경우, **외부 스킬 선별(4번)을 제외한 나머지를 건너뛴다** (호출자가 이미 스탠다드를 정했으므로 재선별 불필요). 4번은 리뷰 대상 도메인 기준이라 coding-standards 주입 여부와 무관하게 항상 실행한다 — only-standards 모드는 어차피 3단계에서 자유 리뷰·외부 스킬 리뷰어를 실행하지 않으므로 좁은 스코프가 유지된다.

1. 사용자에게 **리뷰 대상**을 확인받는다
2. [coding-standards/map.md](../../contexts/coding-standards/map.md)를 읽고, 탐색 절차를 따라 관련 rules·principles 파일을 선별·로드한다 (Swift · UIKit · Clean Architecture/DDD · SPM 기준)
3. 리뷰 대상이 기존 코드베이스 위에서 도는 작업이면, 같은 역할을 하는 기존 구현 패턴(ViewModel 구조, 네트워크 레이어, 재사용 View, Coordinator 구성 등)을 코드베이스에서 직접 탐색해 참조한다. 관련 패턴이 있으면 그 스타일을 리뷰 기준에 함께 반영한다
4. 리뷰 대상 영역에 해당하는 **외부 베스트 프랙티스 스킬**이 설치돼 있으면 추가 컨텍스트로 로드한다 (메인은 Skill tool로 호출. 서브에이전트에 넘길 때는 메인이 형제 스킬 `../<name>/SKILL.md`를 읽어 그 내용을 전달한다). 우리 `coding-standards/`와 권고가 다른 항목이 있으면 사용자에게 보고한다 — 어느 쪽을 따를지 사용자가 결정한다.

   외부 스킬을 적용하는 리뷰는 **sonnet 리뷰어**가 담당한다 (외부 스킬마다 sonnet 리뷰어 1명씩 — default는 단일 리뷰어가 함께 참조, advanced는 3단계 참고). 해당 도메인의 외부 스킬이 없으면 이 단계는 건너뛰고 `coding-standards/`와 자유 리뷰로 진행한다.

   `--extra-standards`(사내 컨벤션)는 외부 스킬 로드를 트리거하지 않는다 — 외부 스킬 선별은 리뷰 대상 도메인으로만 한다.

5. 사용자에게 추가 컨벤션이 있는지 확인한다 (사내 컨벤션 등)

### 2. 리뷰 대상 파악

- PR 본문(description)과 커밋 히스토리를 읽고 변경 의도를 파악한다
- diff를 읽는다
- 이미 달린 코멘트(타인·봇 리뷰 포함)를 읽고, **동일 주제의 지적은 결과 목록에서 완전히 제외**한다. 동의·반박·심각도 교정도 별도 항목으로 올리지 않는다. 새로 발견한 이슈만 나열한다.
- 리뷰 대상은 해당 작성자가 실제로 수정한 코드에 한정한다. 기존 코드의 문제는 리뷰 항목에 포함하지 않는다.
- **테스트 자동 포함**: 구현 파일(View, ViewModel, 유틸, 모델)이 리뷰 대상에 포함되면, 같은 디렉토리 또는 인접 경로에서 해당 테스트 파일(`*Tests.swift` 등)을 탐색하여 리뷰 범위에 자동 포함한다. 요청에 테스트가 명시되지 않았더라도 적용한다. ViewModel의 설계 적절성을 리뷰하면서 테스트 검증 수준을 확인하지 않으면, 구현과 테스트의 결합도·품질 문제를 놓치게 된다.

### 3. 리뷰 수행

#### default 모드

단일 리뷰어 (sonnet) 1명. coding-standards 기반 검증 + 자유 리뷰를 함께 수행하며, 1단계 4번에서 선별된 외부 스킬이 있으면 그 관점도 함께 적용한다.

#### advanced 모드

[CRITICAL] [team-agent](../../contexts/team-agent.md)의 규칙에 따라 팀을 구성한다.

Coding-Standards Reviewer ×N (sonnet), External-Skill Reviewer ×M (sonnet), Advanced Reviewer (opus)를 **병렬 실행**한다.

- **Coding-Standards Reviewer ×N**: coding-standards 영역별로 분할하여 병렬 리뷰
- **External-Skill Reviewer ×M**: 1단계 4번에서 선별된 외부 스킬마다 1명씩 배정한다 (M = 적용 외부 스킬 수, 없으면 0명). 메인이 전달한 해당 외부 스킬(`../<name>/SKILL.md`) 내용만 컨텍스트로 받아 그 관점으로 diff를 리뷰한다.
- **Advanced Reviewer**: diff만 전달, coding-standards 문서·외부 스킬 미전달. 규칙에 없는 문제를 자유 리뷰 시점으로 짚는다.

Lead가 모든 리뷰어의 결과를 종합한다 (중복 제거, 이상한 지적은 사용자에게 확인).

#### only-standards 모드

coding-standards 이슈만 반환. 자유 리뷰·Advanced Reviewer 미실행. 호출자는 `--coding-standards` 경로 명시 권고 (의도 보존).

용도: 신규 코드 작성 전 기존 코드를 새 스탠다드에 맞춰 정렬하는 마이그레이션. 자유 리뷰가 끼면 범위가 흐려지므로 분리.

호출 예: `/code-review <리뷰 대상> --coding-standards <경로들> --mode only-standards`

### 4. 이슈 목록 산출

발견한 이슈를 severity별로 정리하여 반환한다.

- **Critical**: 버그, 보안, 로직 오류
- **Minor**: 컨벤션 위반, 가독성
- **Suggestion**: 개선 제안

컨벤션 기반 지적에는 근거가 되는 컨벤션 파일 경로와 규칙명을 함께 명시한다 (예: `coding-standards/rules/personal/naming.md 「약어로 줄이지 않는다」 위반`).

---

## 후속 연결 (사용자 판단)

이슈 목록 산출 후, 다음 단계는 호출 맥락에 따라 다르다:

- **ios-workflow의 최종 점검(step-6)에서 호출**: step-6이 Implementer에게 수정 지시 → 재리뷰 루프
- **독립 호출**: 사용자가 코멘트할 항목을 직접 선택해 PR에 반영한다
