# Step 6: 최종 점검

모든 기능 구현 및 커밋 완료 후, **PR 생성 직전** 코드 품질을 최종 점검하는 단계입니다.

---

## Step 6.1. Gap Analysis (계획 ↔ 실제 차이 검사)

`pr{N}/persistent/implementation.md` 「구현 순서·커밋 분할」의 계획 커밋 목록과 실제 `git log`를 대조하여 차이를 식별한다.

차이 분류:
- **계획에 있는데 git에 없음** = 누락. 사용자에게 보고
- **git에 있는데 계획에 없음** = 추가. 추가 사유 / 본 PR 범위 vs 별 PR 이연 / 테스트 커버리지 / 「내 작업 외 변경」 위반 가능성을 검증해 보고

차이가 없으면 섹션 생략.

---

## Step 6.1.5. 금지 주석 잔존 점검 (안전망)

별도 sonnet 리뷰어를 spawn해 PR diff에 금지 주석(`// TODO:` 등 잔존 마커)이 남아 있는지 재점검한다. 발견 시 step-5 Implementer 흐름으로 처리 → 다시 Step 6.1.5.

---

## Step 6.2. 리뷰 파이프라인

Lead가 관련 coding-standards를 선별하고 `/code-review`를 advanced 모드로 호출한다.

```
code-review(advanced) → 이슈 목록 → Implementer 수정 → code-review(advanced, 수정 diff만) → 반복 (0건까지)
```

- code-review에 전달하는 입력: PR diff, coding-standards 목록, `reference.md`, 리뷰 모드(advanced)
- 수정은 step-5의 Implementer 흐름이 수행 (마크업 수정이면 figma 원본 대조 기준 / 개인 모드는 사용자 시각 확인)

---

## Step 6.3. 사용자 리뷰 대기

AI 리뷰(Step 6.2) + 모든 수정 완료 후 **사용자가 직접 코드 리뷰**한다. 이 시점까지 stub 커밋부터 IMPL/리뷰 수정 커밋이 그대로 보존되어 있어야 사용자가 stub→IMPL diff를 추적하며 리뷰 가능.

Lead는 현재 커밋 목록을 출력하고 사용자 리뷰 진입을 안내·대기한다. 사용자 리뷰 통과 시 Step 6.4로. 추가 수정 요청 시 step-5 Implementer 처리 → 다시 Step 6.2 → Step 6.3 반복.

---

## Step 6.4. 사용자 동작 테스트

AI 코드 리뷰(6.2) + 사용자 코드 리뷰(6.3) 통과 후, 사용자가 PR 변경분을 직접 실행해 검증할 수 있도록 수동 동작 테스트 시나리오를 작성한다.

산출물: `/plan/pr{N}/consumable/user-test-cases.md`. **수동 동작 테스트 전용** — `it.todo`(자동화 단위 테스트)와 별개이며 함수 단위 케이스는 적지 않는다.

작성 기준:
- 범위: 구현 단계의 모든 코드 변경분을 훑어 TC를 뽑는다
- 케이스 종류: 성공 경로, 실패 경로, 엣지 케이스 모두. iOS 엣지(다크모드·Dynamic Type 최대·회전·백그라운드 복귀·딥링크 진입·빈 상태)를 시나리오에 포함
- 단위: 사용자 인터랙션 시나리오

양식: `- [ ] <시나리오>: <조건>일 때 <기대 동작>`

Lead는 변경분을 훑어 TC 추출 → 파일 작성 후 사용자에게 경로 + 테스트 진입 방법(시뮬레이터 빌드·실행 — [conventions/tuist.md](../conventions/tuist.md)의 `tuist xcodebuild build`) 안내. 사용자 실패 발견 시 수정 지시 → Implementer 처리 → 다시 6.2부터.

step-7에서 PR 본문 Test plan으로 재활용 후 파일 정리한다.

### Step 6.4.1. Figma 시각 대조 + 승인 게이트 (UI 컴포넌트 PR 한정)

UI 컴포넌트 PR이면, 동작 테스트로 사용자가 이미 화면을 띄운 김에 렌더 결과를 `pr{N}/retained/markup.md` 「Figma 원본 링크 인덱스」 URL로 **사용자가 직접 시각 대조**한다.

- 마크업 구현·리뷰는 사용자가 보지 못한 자동 리뷰 루프에서 0건 수렴했으므로, 사용자가 figma 원본을 마주하는 첫 지점이 여기다. 자동 루프가 figma 원본을 잘못 fetch해 멀쩡한 마크업을 어긋난 상태로 수렴시켰을 수 있어, 사람이 진실 원천을 재확인하는 게이트가 필요하다.
- 검증 기준은 figma 원본 직접 fetch (수행 주체만 사람).
- 불일치는 **사용자가 직접 보고 승인/반려**. AI가 figma 차이를 자동으로 정답 처리해 반영하지 않는다.
- 반려분은 Implementer 흐름으로 수정 → 다시 6.2부터.
- **개인 모드**: figma·markup.md가 없다. 사용자가 MARKUP에서 이미 시각 확인을 거쳤으므로 본 게이트는 *조립된 PR 렌더(로직·실데이터 반영)*를 사용자 의도·기획 md(screen.md)와 사용자 눈으로 재확인하는 승인 게이트로 동작한다. 기준이 figma 원본이 아니라 사용자 시각·기획이라는 점만 다르고, 승인/반려 흐름은 동일하다.

---

## Step 6.5. 1회차 커밋 정리·재정렬

사용자 리뷰·동작 테스트 통과 후 step-7 진입 전, stub 커밋을 drop하고 슬라이스별로 커밋을 재정렬한다.

이 정리는 1회차로 `[PR{N}]` 접두사를 유지한다. 본 PR 슬라이스 정리에만 집중하고 메시지 최종화는 마지막 PR로 미룬다.

### Step 6.5.1. 백업 브랜치 [CRITICAL]

history rewriting + force-push가 동반된다. 시작 전 반드시 백업 브랜치를 뜬다: `git branch backup/<현재브랜치>-<YYYYMMDD-HHmm>`. 사고 시 `git reset --hard backup/...`로 복구.

### Step 6.5.2. 케이스 분기

stub 커밋 상태(빈 껍데기 / 본문 안고 있음)에 따라 정리 방식이 갈린다. 케이스별 명령은 [conventions/stub.md](../conventions/stub.md) 「라이프사이클 > 정리」 참조.

### Step 6.5.3. force-push 요청 안내

재정렬 완료 후 사용자에게 force-push 요청. 백업 브랜치 이름 + 재정렬 후 커밋 목록(`git log`)을 보고에 포함.

---

## Step 6.6. decisions.md 최신화

구현·리뷰 과정에서 새로 발생하거나 step-3 작성 시점과 달라진 의사결정을 반영한다. **6.5와 의존 없음 — 병렬 진행 가능.**

---

## Step 6.7. decisions.md 2단 점검

### Step 6.7.1. decisions ↔ 코드 정합 점검 (1차)

검증 소스를 decisions.md, 검증 대상을 현재 코드로 고정해 정합 점검. 코드 수정이 필요하면 step-5 Implementer 흐름.

### Step 6.7.2. 후임자 시각 예상 질문 (2차)

히스토리를 모르는 후임자가 "여기 왜 이렇게 했어요?"라고 물을 만한 질문을 AI가 PR diff + decisions.md 기반으로 추출해 사용자에게 던진다. decisions.md에 이미 있는 결정은 제외. 답할 수 있으면 decisions.md에 추가할지 선택, 어려우면 [/discussion](../../discussion/SKILL.md)으로 토론.

---

## 산출물

결과를 `/plan/pr{N}/consumable/review.md`에 작성한다.

---

## 보고 내용

- Gap Analysis 결과 (차이가 있는 경우)
- code-review 결과: Critical/Minor 이슈 요약
- 사용자 리뷰 통과 여부
- 사용자 동작 테스트 결과
- 사용자 Figma 시각 대조 승인 여부 (UI 컴포넌트 PR)
- 커밋 정리·재정렬 결과 (백업 브랜치 이름 + 재정렬 후 커밋 목록)
- decisions.md 최신화 항목

---

## 산출물 정리

리뷰 파이프라인 완료 + 모든 이슈가 수정 커밋에 반영된 것을 확인한 뒤 `review.md`를 삭제한다.
