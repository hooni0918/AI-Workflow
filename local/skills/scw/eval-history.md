# Eval 기록: workflow 서브에이전트 위임 구조

## 1단계: 위임 트리거 (skill-creator 표준 방식 병행)

서브에이전트에서 스킬을 읽고 "어떻게 하겠다"고 설명하게 하여, 위임 패턴을 인식하는지 테스트. 실제 위임은 불가하지만 인식 여부는 확인 가능.

- 6개 시나리오 × with/without skill = 12 runs
- 결과: 위임 인식 6/6 (100%)
- 발견: 스킬 문서 모호성 3건 (병렬/순차, 코드 접근 경계, assertion 설계 오류)

**주의**: without_skill baseline 에이전트가 working directory의 스킬 파일을 자체 발견하여 오염됨 (5/6). worktree 격리 필요.

## 2단계: E2E (메인 직접 실행)

메인 에이전트가 가상 프로젝트(sum/multiply)에서 step-5 오케스트레이션을 직접 수행.

- 메인 에이전트 → 코드 작성
- review 서브에이전트 → diff 리뷰
- 2 phase 사이클 완료, 커밋 순서 확인

**한계**: toy 프로젝트라 복잡도 부족. 컨벤션별 N개 리뷰 병렬은 미검증.

## 3단계: 세션 분리 인식

"Step 4 끝났습니다" → IMPLEMENTATION_SESSION 전환 안내 여부. skill-creator 표준으로 검증 가능. PASS.

## 4단계: step-5 풀 플로우 + 게이트 차단 (code-review 분리 후)

code-review 독립 스킬 분리(76c2915~9e11801) 후 step-5 오케스트레이션 검증. eval-delegation 방식.

### 시나리오 A — 풀 플로우 (클린 코드)

- mock: React UserCard 컴포넌트 + useUserData hook
- 팀: 7개 에이전트 (markup-impl, feature-impl, figma-reviewer, cs-naming/react/style, advanced-reviewer)
- 검증 항목 10개 → 10/10 PASS (게이트 차단 경로만 부분 PASS)
- Figma→CS→Advanced, CS→Advanced 파이프라인 순서 정상
- Lead 종합 필터링: cs-style 5건을 토큰 미존재로 전건 기각 — 적절한 판단

### 시나리오 B — 게이트 차단 (의도적 위반)

- mock: 의도적 컨벤션 위반 8건 (naming 4, react 2, style 2)
- 1차 CS → 8건 검증 → GATE BLOCKED (Advanced 미실행) → fix → 재CS 0건 → Advanced 진행
- 게이트 차단 경로 PASS

### 교훈

- 1차에서 게이트 차단 미테스트 → 클린 코드만으로는 차단 경로 발동 불가
- eval-delegation.md에 gotcha 추가: "mock은 스킬의 모든 조건 분기를 트리거해야 한다"

## 성과

eval 과정에서 스킬 문서 개선 4건 반영:
1. N개 서브에이전트 인스턴스 병렬 실행 규칙
2. step-5 리뷰 서브에이전트 병렬 명시
3. step-6 병렬 + Gap Analysis 코드 접근 경계
4. 세션 전환 안내 구체적 문구
