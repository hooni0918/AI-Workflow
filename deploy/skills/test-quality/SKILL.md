---
name: test-quality
description: 바뀐 로직에 변이 검사를 돌려 테스트가 실제 오류를 잡는지 실행으로 확인하고, 미해결 변이를 테스트 보강·사용자 질문·판단 기록으로 0건까지 수렴시킨다. "테스트 품질 확인", "변이 검사", "뮤테이션 테스트", "mutation test", "테스트가 오류를 잡는지 확인" 요청 시 사용한다.
argument-hint: "[run | verify]"
---

# 테스트 품질 검사

## 목적

테스트가 통과하는 것을 넘어, 바뀐 로직의 오류를 실제로 잡는지 실행으로 확인하고 미해결 0건까지 수렴시킨다.

판정 기준은 [test-quality.md](../../contexts/testing-strategy/test-quality.md)를 따른다. 이 스킬은 실행 절차만 담는다.

## 전제

- 프로젝트 프로필 `.claude/docs/project-profile.md` 「테스트 품질 검사」 슬롯에서 설정 파일 경로와 적용 수준을 읽는다
- 설정 파일 형식은 [config.example.json](config.example.json)을 따른다. 도구 명령·기준 테스트 명령·모듈 경로는 앱 프로젝트가 소유한다
- 도구는 설정의 `tool.version` 그대로 설치돼 있어야 한다. 없거나 버전이 다르면 미완료다 — 다른 버전으로 대신 돌리지 않는다. swift-mutation-testing은 릴리스 바이너리로 설치한다(소스 빌드는 버전이 `0.0.0-dev`로 찍혀 버전 대조에서 미완료가 된다)

## 적용 수준

프로필 슬롯의 적용 수준 값에 따라 절차를 어디까지 하는지 정한다.

- **필수**: [test-quality.md](../../contexts/testing-strategy/test-quality.md) 「완료 기준」을 채울 때까지 절차를 반복한다. 채우지 못하면 이 검사를 부른 단계를 끝내지 않고, 남은 항목을 보고한다
- **권장**: 절차 1번을 한 번 실행하고 판정을 보고한다. 미해결 처리는 사용자가 요청할 때만 한다
- **미채택**(슬롯이 없거나 `(미채택)`): 실행하지 않고 "변이 검사 미채택"을 보고한다 — 통과로 보고하지 않는다

## 절차

1. 실행한다: `python3 <이 스킬 폴더>/scripts/mutation_gate.py run --config <설정> --out .test-quality/result.json`. 기기·경로처럼 실행 환경마다 다른 값은 `--var 이름=값`으로 넘긴다
2. 판정을 처리한다
   - **통과·해당 없음**: 보고하고 끝낸다
   - **미해결**: 항목마다 원본 요구사항과 대조한다
     - 테스트 누락·약한 단언이면 테스트를 보강한다. 기대값은 test-quality.md 「테스트 의도」를 따른다
     - 요구사항에 답이 없으면 사용자에게 질문한다(test-quality.md 「요구사항에 답이 없을 때」)
     - 결과가 같은 변이·멈춤·충돌, 변이 대상이 아닌 표기면 판단 기록 초안(`key`·`file`·`line_text`·`kind`·`reason`)을 근거와 함께 사용자에게 제안한다
   - **미완료**: 출력의 사유(기준 테스트 실패·도구 미설치·설정 밖 변경 등)를 해소하고 다시 실행한다
3. 보강·결정이 끝날 때마다 다시 실행한다. 어디까지 반복하는지는 「적용 수준」을 따른다
4. 그 뒤 코드가 또 바뀌었으면 `python3 <이 스킬 폴더>/scripts/mutation_gate.py verify --config <설정> --result .test-quality/result.json`로 결과가 지금 코드에 유효한지 확인한다. 0이 아니면 1번부터 다시 한다

종료 코드: 0 통과·해당 없음 / 1 미해결 / 2 미완료 / 3 설정 오류. 도구·기준 테스트 출력은 `run`이 알려 주는 작업 폴더에 남는다.

## 판단 기록

- 위치: `.test-quality/decisions.json` (고정, 앱 레포에 커밋)
- 형식: `{"version": 1, "decisions": [{"key", "file", "line_text", "kind", "reason", "approved_by"}]}`. `key`·`file`·`line_text`는 실행 출력의 미해결 항목에서 옮긴다(`key=` 값, 파일 경로, 그 아래 줄 내용). 셋이 모두 실제 변이와 맞아야 해소된다
- `kind`와 해소할 수 있는 상태: `equivalent`(Survived·NoCoverage), `hang_detected`(Timeout), `crash_detected`(RuntimeError), `ignore_approved`(Ignored), `no_mutant_expected`(NoMutant — 실행기가 올린 변이 없음)
- 항목이 빠지거나 비어 있는 기록은 실행기가 쓰지 않고 `invalid_decisions`로 센다
- AI는 `approved_by`를 쓰지 않는다 — 사용자가 근거를 확인하고 직접 채운다
- 보호 훅은 보조 수단이다. 전역 설치(`make sync-system`)의 Claude에서는 판단 기록·검사 설정·결과·도구 설정·CI 워크플로를 고치려 하면 허락 창을 띄우고, Codex에서는 막는다 — Codex에서는 사용자가 직접 편집한다. 플러그인 설치에는 이 훅이 없다. 실제 강제는 앱 레포의 CODEOWNERS 리뷰와 CI가 맡는다

## 보고

- 판정, 검출·미해결·판단 기록 해소 수, 미해결 항목별 처리(보강·질문·기록 제안), 미완료 사유, 결과 파일 경로
- 도구 미설치·미완료는 그대로 보고한다. 문서 수정만으로 검사가 도입됐다고 보고하지 않는다
