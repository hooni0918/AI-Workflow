# deploy/base-settings.json의 공통 hook 정의를 타겟별 hook 구조로 변환한다.
#
# base.hooks는 논리 목록(file/event/on/msg)이고, 타겟마다 hook 런타임이 달라서
# (codex엔 SendMessage tool·UserPromptSubmit 없음, PreToolUse를 '*'로 통합) 타겟별
# 어댑터가 matcher·이벤트 구조를 변환한다.
#
# 비-hook 설정(model·permissions 등)은 공통이 아니라 타겟별이므로 base가 아니라 각
# 타겟 override 파일(deploy/claude-settings.json 등)에 둔다 (deploy_lib.py가 머지).
# 타겟이 추가·변경되면 HOOK_ADAPTERS / 호출부 rule만 고치면 된다 (단일 출처).
import os

# base-settings.json에 적힌 hook 파일명을 그대로 사용한다.
def hook_py_name(name):
    return name


# matcher() 반환이 None이면 그 그룹은 matcher 키 없이 출력된다(예: UserPromptSubmit).
HOOK_ADAPTERS = {
    "claude": {
        "dir": ".claude",
        "supports": lambda event, on: True,
        "matcher": lambda event, on: None
        if event == "UserPromptSubmit"
        else {
            "write": "Write",
            "bash": "Bash",
            "message": "SendMessage",
            "enterworktree": "EnterWorktree",
            "search": ["Glob", "Grep"],
        }.get(on),
    },
    "codex": {
        # codex엔 SendMessage·EnterWorktree tool·UserPromptSubmit가 없다.
        # PreToolUse 정책 훅은 도구명 분리 대신 '*'로 전부 잡는다.
        "dir": ".codex",
        "supports": lambda event, on: event != "UserPromptSubmit" and on != "enterworktree",
        "matcher": lambda event, on: "*"
        if event == "PreToolUse"
        else {"write": "Write", "bash": "Bash"}.get(on),
    },
}

NO_MATCHER = " nomatcher"


# 전역판 hook 명령: homedir 절대경로로 python3 hook 실행.
def hook_command(dir_name, file):
    abs_path = os.path.join(os.path.expanduser("~"), dir_name, "hooks", hook_py_name(file))
    return f'python3 "{abs_path}"'


# 로컬판 hook 명령: cwd=repo root 기준 상대 경로. codex에서 검증된 형식이며 전역의
# 절대경로 형식과 의도적으로 분기한다(산출물이 repo 안에 있어 절대경로 불필요).
def local_hook_command(dir_name, file):
    return f"python3 {dir_name}/hooks/{hook_py_name(file)}"


# 로컬판(repo-local .claude/.codex 산출물)용 어댑터. 전역과 메커니즘은 같고 분기점만
# 다르다: command가 repo-relative(local_hook_command)이고, codex 매처는 사용자가 codex로
# 검증한 run_command+Bash다(전역의 '*'는 프로젝트-로컬 발화 미검증이라 검증된 값 사용).
LOCAL_ADAPTERS = {
    "claude": {
        "dir": ".claude",
        "supports": lambda event, on: True,
        "matcher": lambda event, on: {"bash": "Bash"}.get(on),
    },
    "codex": {
        "dir": ".codex",
        "supports": lambda event, on: event != "UserPromptSubmit" and on != "enterworktree",
        "matcher": lambda event, on: {"bash": ["run_command", "Bash"]}.get(on),
    },
}


# 논리 hook 목록 → 타겟별 hooks 객체 { event: [ { matcher?, hooks:[...] } ] }
# base 목록 순서를 보존하고, 같은 (event, matcher)는 한 그룹으로 묶는다.
# opts로 어댑터·command 생성기를 주입하면 로컬판을 만들 수 있다(미지정 시 전역 동작).
def build_hooks(logical_hooks, target_name, opts=None):
    opts = opts or {}
    adapters = opts.get("adapters") or HOOK_ADAPTERS
    make_command = opts.get("makeCommand") or hook_command
    adapter = adapters.get(target_name)
    if not adapter:
        raise RuntimeError(f"알 수 없는 hook 타겟: {target_name}")

    by_event = {}
    for h in logical_hooks:
        if not adapter["supports"](h["event"], h["on"]):
            continue
        matcher_val = adapter["matcher"](h["event"], h["on"])
        # matcher는 str | list[str] | None. 리스트면 매처별로 같은 hook을 fan-out한다.
        matchers = matcher_val if isinstance(matcher_val, list) else [matcher_val]
        for matcher in matchers:
            groups = by_event.setdefault(h["event"], [])
            key = NO_MATCHER if matcher is None else matcher
            group = next((g for g in groups if g["key"] == key), None)
            if group is None:
                group = {"key": key, "matcher": matcher, "hooks": []}
                groups.append(group)
            group["hooks"].append(
                {
                    "type": "command",
                    "command": make_command(adapter["dir"], h["file"]),
                    "statusMessage": h["msg"],
                }
            )

    # 내부 key 제거 + matcher 키가 hooks보다 먼저 오도록 재구성.
    result = {}
    for event in by_event:
        out_groups = []
        for g in by_event[event]:
            out = {}
            if g["matcher"] is not None:
                out["matcher"] = g["matcher"]
            out["hooks"] = g["hooks"]
            out_groups.append(out)
        result[event] = out_groups
    return result
