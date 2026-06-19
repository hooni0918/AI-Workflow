# Trigger Eval Bench

스킬 description의 트리거 정확도(false negative/positive)를 측정한다.

[CRITICAL] 작업 시작 전 「현재 상태」와 「피해야 할 함정」을 반드시 읽는다. 같은 6시간 함정 재발 방지용이다.

## 현재 상태 (2026-05-16 기준)

**skill-creator 표준 도구(`run_eval.py`, `run_loop.py`)는 현재 broken**. Anthropic 공식 fix 없음. 모든 관련 이슈·PR OPEN 상태.

알려진 3가지 별개 문제:

| 문제 | 영향 | 출처 |
|---|---|---|
| `claude -p`가 `.claude/commands/` 로드 안 함 (architectural) | 모든 OS — 모든 should-trigger 쿼리 0% recall | [anthropics/skills#556](https://github.com/anthropics/skills/issues/556), [anthropics/claude-code#36570](https://github.com/anthropics/claude-code/issues/36570) |
| Parallel worker UUID 충돌 (`--num-workers 10` default) | 모든 OS — `--num-workers 1`은 100%, default는 11% | [PR #794 OPEN](https://github.com/anthropics/skills/pull/794) |
| 윈도우 `select.select` pipe fd 비호환 (WinError 10038) | 윈도우만 — 모든 쿼리 실패 | 미보고 |

**근거**: hysteric-lab의 분석 (2026-05-10, 285 trials, 공식 docs https://code.claude.com/docs/en/headless 인용): "User-invoked skills like `/commit` and built-in commands are only available in interactive mode. In `-p` mode, describe the task you want to accomplish instead." `run_eval.py:53-54`가 test artifact를 `.claude/commands/`에 쓰는데 `claude -p`는 commands 안 봄 → 구조적 broken.

윈도우 patch만으로 해결 안 됨. 표준 도구 자체가 구조적으로 동작 안 함.

## 측정 도구: bench-trigger.py

표준 도구가 broken이라 자체 도구 `scripts/bench-trigger.py` 사용. 동작 원리:

- `claude -p`로 query 호출, `--output-format stream-json`으로 trigger 신호 캡처
- **`.claude/commands/` 임시 파일 안 만들고**, 측정 대상 `SKILL.md` 자체를 그대로 사용 (skills 디렉토리는 `claude -p`도 인식)
- `subprocess.Popen` + reader thread + `queue.Queue` 패턴으로 stream-json을 line-by-line 소비. `select.select`이 윈도우 파이프 fd를 못 받는 문제 우회
- `Skill` tool_use 감지 즉시 `process.kill()` — early termination. trigger-positive 쿼리도 ~10s 안에 종료. 본문 작업까지 대기하면 130s+

hysteric-lab이 제안한 fix(`commands/` → `skills/`)와 같은 방향을 자체 구현한 것. 우연이 아니라 broken 표준의 자연스러운 우회.

## 입력 eval set

```json
[
  {"query": "사용자가 입력할 만한 문장 (구체적·현실적, 백스토리 포함)", "should_trigger": true},
  {"query": "트리거되면 안 되는 문장 (인접 도메인 함정 포함)", "should_trigger": false}
]
```

should-trigger 8~12개, should-not-trigger 8~12개 (near-miss 위주). UTF-8 BOM 금지 (Python json 파서 실패).

## 호출

```powershell
$env:PYTHONUTF8 = "1"
& python.exe <scw>/scripts/bench-trigger.py `
  --eval-set <path-to-eval.json> `
  --skill-path <path-to-skill-dir> `
  --runs-per-query 3 `
  --num-workers 3 `
  --timeout 240 `
  --model claude-sonnet-4-6 `
  --out <result.json> `
  --verbose
```

- `--skill-path`: 실제 측정 대상. **별도 워크트리 안의 `local/skills/<name>/`** 권장 (아래 「안전 절차」 참조).
- `--runs-per-query 3`: LLM 비결정성 보정. 3 권장.
- `--num-workers 3`: 윈도우에선 동시 `claude -p` 부하 고려. 5+로 늘리면 socket·메모리 한계.
- 모델: sonnet (SCW 「Eval」 룰).
- `--timeout 240`: 90·120으로는 부족. trigger되는 쿼리는 본문 작업 130s+ 걸리는데 early-kill 신호 못 잡으면 통째 timeout. 240 권장.

**시간 추정**: early-kill 덕에 trigger되는 쿼리는 ~10~15s, non-trigger는 응답 완료까지 ~20~30s. `22 × 3 / 3 workers × 평균 20s ≈ 7~10분` per round.

## 결과 해석

JSON 핵심 필드:
- `summary.passed/total` — 통과 비율
- `summary.should_trigger_triggered_rate` — 평균 trigger rate (0.7+ 권장)
- `summary.should_not_trigger_triggered_rate` — false positive (0.0~0.1)
- `results[].rate` — 쿼리별 trigger 비율 (M/N runs)

FAIL 분류:
- **핵심 진입 신호 누락** → description에 자연어 키워드 추가
- **모호한 케이스** → 안 잡혀도 무방. false positive 위험이 더 큼
- **변동성 (rate 0.3~0.6)** → LLM 비결정성. description 신호 약함, 보강 후 재측정
- **추상 쿼리 (예: "description 너무 길어")** → claude가 자체 답변. 어떤 description으로도 trigger 안 됨. eval set 품질 문제이지 description 문제 아님 (skill-creator 본문: "Simple queries... won't trigger skills regardless of description quality").

## 안전 절차 — SKILL.md swap이 위험한 이유

bench-trigger.py는 측정 대상 SKILL.md를 **현 상태 그대로 측정**한다. description 변경 효과 비교(BEFORE/AFTER)를 하려면 SKILL.md를 일시 변경해야 하는데, **메인 워크트리의 SKILL.md를 swap하면 사용자의 다른 세션이 그 swap 상태로 실제 사용 영향**을 받는다.

[CRITICAL] description 비교 측정은 **반드시 별도 워크트리**에서 수행한다:

```powershell
# scw 워크트리 만들기 (master 위에 ahead 있는 경우 worktree 룰 발동)
git -C <AC> worktree add ../<AC>-scw-bench -b chore/scw-<topic> <base-commit>

# 그 워크트리 안의 SKILL.md만 수정·측정
cd ../<AC>-scw-bench
# Edit local/skills/<name>/SKILL.md line 3 description
# bench-trigger.py --skill-path ./local/skills/<name>
```

이렇게 하면 메인 워크트리의 실제 사용 환경은 영향 없음.

[CRITICAL] **측정 시작 직전 워크트리 description 상태를 반드시 확인한다**. 사용자 또는 다른 세션이 wip로 description을 미리 바꿔놓았을 수 있다 — 그 상태로 측정하면 BEFORE/AFTER가 사실은 같은 description 두 번 측정이라 delta 0이 "변경 효과 없음"이 아니라 "변경 자체가 없었음"이 된다. 측정 전 `git diff <base>..HEAD -- local/skills/<name>/SKILL.md`로 description 라인이 base와 같은지 확인. wip로 변경돼 있으면 wip 풀거나 명확한 base commit 위에서 워크트리 재생성.

## 자동화: run_loop의 대체

`skill-creator`의 `run_loop.py`는 자동 5-iteration 최적화(eval + improve_description + iterate + train/test split + best_description 선정) 도구지만 위의 architectural 이슈로 broken. bench-trigger.py는 측정만 wrapping, 자동 루프 미구현.

자동 루프 옵션:
- **수동 라운드**: description 한 줄 수정 → bench-trigger.py 측정 → 잔류 FAIL 패턴 분석 → 또 수정 → 반복. 라운드당 7~10분. **최대 3~4 라운드까지만 시도** (그 이상은 LLM 비결정성에 묻힘).
- **`improve_description.py` 직접 호출 + bench-trigger.py 측정 자체 wrapping**: 미구현. 만들 가치 있으나 함정(commands 안 거치고 description override가 호출자 환경에 어떻게 전달되는지) 검증 필요.
- **hysteric-lab의 manual workaround**: 50줄 bash + 사람 눈 verdict. 가장 신뢰 가능. 자동화 X.

## 함정 — 피해야 할 6시간 사례

직전 세션이 빠진 함정 패턴 (재발 시 같은 시간 낭비):

| 함정 | 증상 | 예방 |
|---|---|---|
| 표준 도구 patch만으로 해결된다고 판단 | `select.select` 윈도우 fix만 적용 → 여전히 0% recall (architectural 이슈 별도) | 「현재 상태」3가지 문제 다 확인 후 결정 |
| mini test 부실 검증 | exit code 0 + JSON 출력만 보고 "동작"이라 판단. stderr WinError 무시 → 0/1 trigger를 "정상 0 trigger"로 해석 | stderr 끝까지 확인. WinError·Warning 텍스트 grep |
| 메인 워크트리에서 SKILL.md swap | description 측정 중 사용자 다른 세션이 swap 상태로 실제 사용 → 충돌 commit·index 오염 | 별도 워크트리 필수 (위 「안전 절차」) |
| 측정 직전 워크트리 description 미확인 | 다른 세션 wip가 워크트리 description을 이미 swap한 채로 R1/R2 측정 → 같은 description 두 번 측정, delta 0이 "변경 효과 없음"으로 오해석 | 측정 시작 전 `git diff <base>..HEAD -- SKILL.md` 필수. wip 보이면 풀거나 base commit 위에서 워크트리 재생성 |
| timeout 부족으로 trigger 케이스 모두 dropout | timeout=60·90으로 측정 → trigger되는 쿼리는 본문 작업까지 130s+ 걸려 다 timeout. should_trigger rate=0%로 잘못 잡힘. early-kill이 stream signal 못 잡으면 timeout까지 진행 | `--timeout 240` 기본값. early-kill 기제가 ttft 8~10s 후 trigger 감지 즉시 kill하므로 정상이면 비싸지 않음 |
| 라운드 무한 반복 | "0건 수렴까지" 룰 글자대로 따라 5+ 라운드 → LLM 비결정성에 묻힘, 시간 낭비 | 3~4 라운드에서 정체면 description 외 요인(scw 본문 구조, eval set 품질) 재검토 |
| eval set 작성 시 노골적 인용 | description에 eval 쿼리 표현 그대로 박아넣음 (overfitting) → 측정 과정에선 통과해도 실제 사용성 X | 의도 표현으로 일반화. eval 쿼리는 표본일 뿐 |
| Anthropic 표준 가정 무비판 신뢰 | "skill-creator 플러그인이 표준이라 동작할 것" → 6시간 후 broken 확인 | GitHub 이슈/PR 먼저 검색. 표준 도구도 broken 가능 |
| non-trigger run이 cwd 오염 | 트리거 안 되는 액션형 쿼리는 `claude -p`가 본문 작업까지 수행 → repo 루트에 파일 생성·`git add`까지 함(early-kill은 트리거 시에만 발동). 측정 후 stray 산출물 잔존 | 글로벌 스킬 측정은 빈 scratch 디렉토리에서 실행(`find_project_root`가 cwd로 fallback). 로컬 스킬은 in-repo 불가피하니 측정 직후 `git status`로 stray 파일·staging 점검·정리 필수 |
| disclaimer만으로 자동 트리거 차단 시도 | description에 "자동 트리거하지 않는다"를 붙여도 도메인 의미 매칭(bait)이 남으면 강매칭 쿼리에서 누설(실측 0.30) | 명시 호출 전용 스킬은 도메인 키워드를 description에서 제거하고 제약만 남긴다(bait 제거). 실측 0.30→0.00 수렴 |

## Limitations

- 트리거 결정은 모델별로 다름. 측정 모델과 사용자 환경 모델 다르면 결과 해석 주의.
- timeout 짧으면 false negative.
- 트리거 감지는 stream-json의 `Skill` tool_use에서 `"skill":"<name>"` 매칭. 다른 tool 형태는 미감지.
- bench-trigger.py는 표준 도구가 fix되면 폐기 대상. PR #794 + hysteric-lab의 `commands → skills` fix가 merge되면 표준 도구로 전환.

## 워크스페이스 컨벤션

```
$env:TEMP/<skill>-trigger-eval/
  eval_set.json                  # UTF-8 BOM 없이
  iteration-1/
    before.json + before.log
    after.json + after.log
  iteration-2/                    # 라운드 추가 시
    ...
```

작업 종료 후 `Remove-Item -Recurse -Force $env:TEMP/<skill>-trigger-eval/` 정리.
