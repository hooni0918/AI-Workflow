# Step 4: 최종 점검

IMPL 세션에서 기능 구현·커밋(step-3)을 마친 뒤, **PR 생성 직전** 코드 품질을 최종 점검하는 단계다. 통과하면 WRITING(step-5)으로 PR 본문을 작성한다.

---

## Step 4.1. Gap Analysis (계획 ↔ 실제 차이 검사)

`pr{N}/persistent/implementation.md` 「구현 순서·커밋 분할」의 계획 커밋 목록과 실제 `git log`를 대조하여 차이를 식별한다.

차이 분류:
- **계획에 있는데 git에 없음** = 누락. 사용자에게 보고
- **git에 있는데 계획에 없음** = 추가. 추가 사유 / 본 PR 범위 vs 별 PR 이연 / 테스트 커버리지 / 「내 작업 외 변경」 위반 가능성을 검증해 보고

차이가 없으면 섹션 생략.

---

## Step 4.1.5. 금지 주석 잔존 점검 (안전망)

별도 sonnet 리뷰어를 spawn해 PR diff에 금지 주석(`// TODO:`·`// TODO [AI_IMPL]:` 등 잔존 마커)이 남아 있는지 재점검한다. IMPL 종료 시 이 마커는 **0건**이어야 한다 — PR 이연·외부 의존은 `project.md`·`overview.md`로 관리한다. 발견 시 step-3 Implementer 흐름으로 처리 → 다시 Step 4.1.5.

---

## Step 4.2. 기계 게이트 3종

`flutter analyze`·`flutter test`와 별개로, PR 생성 전 아래 3종 기계 게이트를 실행한다. 명령·판정 기준은 [conventions/commands.md](../conventions/commands.md) 참조.

1. **codegen drift**: `dart run build_runner build --delete-conflicting-outputs` 재실행 후 `git diff` 0건. 커밋된 `*.g.dart`가 신선 산출물과 일치해야 한다 (신규 DTO의 `.g.dart` 커밋은 정상 — 기준은 "무변경"이 아니라 "재생성해도 동일").
2. **l10n drift**: 문구(`strings.yaml`) 변경이 있으면 `flutter/l10n`에서 `dart run generate.dart --check`.
3. **pubspec.lock**: 의도된 의존성 변경 외 diff 0건 (무관 churn 커밋 금지 — 「내 작업 외 변경」 위반).

게이트 실패 시 step-3 Implementer 흐름으로 수정 → 다시 이 단계.

---

## Step 4.3. 리뷰 파이프라인

Lead가 [/code-review](../../code-review/SKILL.md)를 advanced 모드로 호출한다. **`--coding-standards`에 flutter 소스를 반드시 명시 주입**한다 — 미주입 시 code-review가 이 스킬과 무관한 기본 폴백 규칙 맵을 로드하므로 금지.

- `--coding-standards`: [conventions/review-checklist.md](../conventions/review-checklist.md) (리뷰 채굴 규칙, 로컬 전용 캐시)
- `--extra-standards`: 레퍼런스 PR 코드 경로(`reference.md` 인덱스) + 프로젝트 `analysis_options.yaml`
- 입력: PR diff, 위 주입, 리뷰 모드(advanced)
- flutter 전용 외부 베스트프랙티스 스킬은 미설치 — code-review의 외부 스킬 선별은 0건

```
code-review(advanced) → 이슈 목록 → Implementer 수정 → code-review(advanced, 수정 diff만) → 반복 (0건까지)
```

수정은 step-3의 Implementer 흐름이 수행한다 (UI 수정이면 figma 원본 대조 기준, figma 없으면 사용자 시각 확인).

---

## Step 4.4. 사용자 리뷰 대기

AI 리뷰(Step 4.3) + 모든 수정 완료 후 **사용자가 직접 코드 리뷰**한다. 이 시점까지 IMPL 커밋부터 리뷰 수정 커밋이 그대로 보존되어 있어야 사용자가 커밋별 diff를 추적하며 리뷰할 수 있다.

Lead는 현재 커밋 목록을 출력하고 사용자 리뷰 진입을 안내·대기한다. 사용자 리뷰 통과 시 Step 4.5로. 추가 수정 요청 시 step-3 Implementer 처리 → 다시 Step 4.3 → Step 4.4 반복.

---

## Step 4.5. 사용자 동작 테스트

AI 코드 리뷰(4.3) + 사용자 코드 리뷰(4.4) 통과 후, 사용자가 PR 변경분을 직접 실행해 검증할 수 있도록 수동 동작 테스트 시나리오를 작성한다.

산출물: `/plan/pr{N}/consumable/user-test-cases.md`. **수동 동작 테스트 전용** — 테스트 TODO(자동화 단위 테스트)와 별개이며 함수 단위 케이스는 적지 않는다.

작성 기준:
- 범위: 구현 단계의 모든 코드 변경분을 훑어 TC를 뽑는다
- 케이스 종류: 성공 경로, 실패 경로, 엣지 케이스 모두. 모바일 엣지(다크모드·텍스트 스케일 최대(`MediaQuery.textScaler`)·회전·백그라운드 복귀·딥링크 진입·빈 상태)를 시나리오에 포함
- 단위: 사용자 인터랙션 시나리오

양식: `- [ ] <시나리오>: <조건>일 때 <기대 동작>`

프로젝트 프로필(`.claude/docs/project-profile.md`)에 「동작 테스트 자동화」 슬롯이 정의되어 있으면, 사용자 수동 테스트 전에 그 슬롯이 가리키는 스킬을 소환해 `user-test-cases.md` 시나리오를 자동 실행시키고 판정 리포트를 받는다. PASS 항목은 `- [x]`로 표시하고, 판정 보류·FAIL 항목만 사용자 수동 확인 대상으로 안내한다. 리포트는 `/plan/pr{N}/consumable/`에 남겨 step-5 Test plan에 첨부한다. 슬롯이 없으면 아래 수동 절차를 그대로 따른다.

Lead는 변경분을 훑어 TC 추출 → 파일 작성 후 사용자에게 경로 + 테스트 진입 방법(`flutter run` — [conventions/commands.md](../conventions/commands.md)) 안내. 배선·DI·bloc이 걸린 변경은 hot reload가 `main()`/DI/bloc을 재초기화하지 않아 거짓 통과하므로, 조립 렌더 확인은 반드시 **hot restart**로 한다. 사용자 실패 발견 시 수정 지시 → Implementer 처리 → 다시 4.3부터.

step-5에서 PR 본문 Test plan으로 재활용 후 파일 정리한다.

### Step 4.5.1. Figma 시각 대조 + 승인 게이트 (UI 컴포넌트 PR 한정)

UI 컴포넌트 PR이면, 동작 테스트로 사용자가 이미 화면을 띄운 김에 렌더 결과를 `retained/figma-url.md` 「Figma 원본 링크 인덱스」 URL로 **사용자가 직접 시각 대조**한다.

- UI 구현·리뷰는 사용자가 보지 못한 자동 리뷰 루프에서 0건 수렴했으므로, 사용자가 figma 원본을 마주하는 첫 지점이 여기다. 자동 루프가 figma 원본을 잘못 fetch해 멀쩡한 화면을 어긋난 상태로 수렴시켰을 수 있어, 사람이 진실 원천을 재확인하는 게이트가 필요하다.
- 검증 기준은 figma 원본 직접 fetch (수행 주체만 사람).
- 불일치는 **사용자가 직접 보고 승인/반려**. AI가 figma 차이를 자동으로 정답 처리해 반영하지 않는다.
- 반려분은 Implementer 흐름으로 수정 → 다시 4.3부터.
- **figma가 없으면**: 본 게이트는 *조립된 PR 렌더(로직·실데이터 반영)*를 사용자 의도·기획 md(`screen.md`)와 사용자 눈으로 재확인하는 승인 게이트로 동작한다. 기준이 figma 원본이 아니라 사용자 시각·기획이라는 점만 다르고, 승인/반려 흐름은 동일하다.

---

## Step 4.6. 1회차 커밋 정리·재정렬

사용자 리뷰·동작 테스트 통과 후 step-5 진입 전, 리뷰 수정 커밋을 슬라이스별로 squash·재정렬한다.

이 정리는 1회차로 `[PR{N}]` 접두사를 유지한다. 본 PR 슬라이스 정리에만 집중하고 메시지 최종화는 마지막 PR로 미룬다.

### Step 4.6.1. 백업 브랜치 [CRITICAL]

history rewriting + force-push가 동반된다. 시작 전 반드시 백업 브랜치를 뜬다: `git branch backup/<현재브랜치>-<YYYYMMDD-HHmm>`. 사고 시 `git reset --hard backup/...`로 복구.

### Step 4.6.2. 슬라이스별 squash

구현·리뷰 과정에서 쌓인 리뷰 수정 커밋을 각 기능 슬라이스 커밋으로 fixup·squash한다. 실측 커밋 순서(domain→data→UI)를 유지하되, 리뷰에서 파생된 수정은 원 슬라이스에 흡수해 커밋 하나가 독립적으로 설명·테스트되는 상태로 남긴다.

### Step 4.6.3. force-push 요청 안내

재정렬 완료 후 사용자에게 force-push 요청. 백업 브랜치 이름 + 재정렬 후 커밋 목록(`git log`)을 보고에 포함.

---

## Step 4.7. decisions.md 최신화

구현·리뷰 과정에서 새로 발생하거나 step-2 작성 시점과 달라진 의사결정을 반영한다. **4.6과 의존 없음 — 병렬 진행 가능.**

---

## Step 4.8. decisions.md 2단 점검

### Step 4.8.1. decisions ↔ 코드 정합 점검 (1차)

검증 소스를 decisions.md, 검증 대상을 현재 코드로 고정해 정합 점검. 코드 수정이 필요하면 step-3 Implementer 흐름.

### Step 4.8.2. 후임자 시각 예상 질문 (2차)

히스토리를 모르는 후임자가 "여기 왜 이렇게 했어요?"라고 물을 만한 질문을 AI가 PR diff + decisions.md 기반으로 추출해 사용자에게 던진다. decisions.md에 이미 있는 결정은 제외. 답할 수 있으면 decisions.md에 추가할지 선택, 어려우면 [/discussion](../../discussion/SKILL.md)으로 토론.

---

## 산출물

결과를 `/plan/pr{N}/consumable/review.md`에 작성한다.

---

## 보고 내용

- Gap Analysis 결과 (차이가 있는 경우)
- 기계 게이트 3종 결과 (codegen·l10n·pubspec.lock)
- code-review 결과: Critical/Minor 이슈 요약
- 사용자 리뷰 통과 여부
- 사용자 동작 테스트 결과
- 사용자 Figma 시각 대조 승인 여부 (UI 컴포넌트 PR)
- 커밋 정리·재정렬 결과 (백업 브랜치 이름 + 재정렬 후 커밋 목록)
- decisions.md 최신화 항목

---

## 산출물 정리

리뷰 파이프라인 완료 + 모든 이슈가 수정 커밋에 반영된 것을 확인한 뒤 `review.md`를 삭제한다.

---

## Step 4 종료 — 분기점

step-4는 IMPL 세션의 마지막 step = 세션 분기점이다. 이 단계까지 통과하면 IMPL 세션이 끝난다. 보고 출력 직후 SKILL.md 「세션 spawn 안내 메커니즘」을 발동하여 후속 **WRITING** 세션(step-5, PR 본문) spawn 안내를 출력한다. 멀티 PR이어도 "머지 후 다음 PLAN" 안내는 여기가 아니라 WRITING(step-5) 종료에서 낸다.
