# 팀/서브에이전트 운용 규칙

역할별 작업자를 오래 유지하거나 다라운드 리뷰를 돌려야 할 때, 현재 런타임에서 제공되는 에이전트 기능을 기준으로 선택한다. Claude Code와 Codex는 도구 이름과 수명주기가 다르므로 `TeamCreate`를 모든 환경의 기본값으로 가정하지 않는다.

## Claude Code

Agent Teams를 사용할 수 있으면 다음 절차를 따른다.

1. **TeamCreate**로 팀 생성 (이미 있으면 생략)
2. **Agent** 호출 시 `team_name` 파라미터 포함
3. 에이전트 간 후속 지시는 **SendMessage**로 전달

`team_name` 없이 호출하면 일회성 서브에이전트가 되어 다라운드 SendMessage 소통이 불가능하다.

## Codex

Codex에서 `TeamCreate` / `SendMessage`가 제공되지 않으면, 현재 세션의 도구 정책이 허용하는 범위에서 subagent 도구로 대체한다.

- 새 역할 작업자가 필요하면 `spawn_agent`를 사용한다.
- 같은 역할 작업자에게 후속 지시가 필요하면 기존 agent id에 `send_input`을 사용한다.
- 즉시 결과가 다음 단계의 블로커일 때만 `wait_agent`로 기다린다.
- subagent 도구가 없거나 사용 조건이 맞지 않으면 메인이 직접 수행하고, 팀 구조를 만들 수 없는 이유를 사용자에게 보고한다.

Codex subagent는 Claude Agent Teams처럼 영구 팀 이름을 공유하지 않는다. 여러 라운드를 이어가야 하면 에이전트 id를 재사용하는 방식으로 세션 내 맥락을 유지한다.
