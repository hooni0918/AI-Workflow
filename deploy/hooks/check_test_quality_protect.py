#!/usr/bin/env python3
"""변이 검사 판정 파일 보호 훅.

test_quality_protected.txt에 적힌 파일(판단 기록·검사 설정·결과·도구 설정·CI 워크플로)을 AI가 고치려
하면 사용자 허락을 받는다. 판단 기록은 "사람이 승인한 기록만 해소"가 기준이라, AI가 승인자까지
채우면 자기 승인이 된다.

- Claude: permissionDecision "ask" — 실행 직전에 허락 창을 띄운다. auto 모드에서도 뜬다.
- Codex: "ask"를 지원하지 않아 deny로 막고 사용자가 직접 고치게 한다.

문자열 대조라 스크립트 파일을 거치는 간접 쓰기 등은 잡지 못한다. 보조 수단이며, 실제 강제는 앱
레포의 CODEOWNERS 리뷰와 CI가 맡는다.

보는 것:
- Edit·Write: file_path. Codex apply_patch: 패치 머리줄의 파일 경로 (본문은 보지 않는다)
- Bash·Monitor: 명령을 구간(; && || | 등)으로 나눠 본다. 게이트(mutation_gate.py)의 run·verify·
  plan·check-config 구간과 읽기 전용 명령(cat·grep·git status·git add 등) 구간은 쓰기 리다이렉트
  대상만 본다. judge 는 손으로 만든 보고서로 결과를 쓸 수 있어 면제하지 않는다.
  경로를 적지 않고 작업 트리 전체를 바꾸는 git 명령(apply·am·stash pop·하드 리셋·checkout .)은
  .test-quality/ 가 있는 레포에서만 묻는다 — 다른 레포에서는 묻지 않는다
- 그 밖의 도구와 description 같은 다른 입력은 보지 않는다
"""
import json
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import deny, get_cwd, read_payload  # noqa: E402

PROTECTED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_quality_protected.txt")

_FILE_TOOLS = ("Edit", "Write")
_SHELL_TOOLS = ("Bash", "Monitor")
_PATCH_HEADER = re.compile(r"^\*\*\* (?:(?:Add|Update|Delete) File|Move to): (.+)$", re.MULTILINE)
_SEPARATORS = {";", "&&", "||", "|", "&", "|&", "(", ")", ";;"}
_WRITE_REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
_SKIP_NEXT = {"<", "<<", "<<<", ">&", "<&", "<>"}
_GATE_EXEMPT = {"run", "verify", "plan", "check-config"}
_READ_ONLY = {"cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "ls", "wc", "diff",
              "stat", "file", "jq", "tree", "echo", "printf", "true"}
_GIT_READ_ONLY = {"status", "diff", "log", "show", "blame", "ls-files", "add", "grep", "rev-parse"}
_GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree"}


def is_codex():
    return "/.codex/" in os.path.abspath(__file__).replace("\\", "/")


def load_patterns():
    try:
        with open(PROTECTED_FILE, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def hits(text, patterns):
    # "이름/" 은 그 이름의 폴더 아래 전부. 그 밖은 파일 — cd 뒤처럼 폴더 없이 이름만 적혀도 잡도록 파일 이름으로 본다
    text = text.replace("\\", "/")
    found = []
    for pattern in patterns:
        if pattern.endswith("/"):
            if re.search(r"(?<![\w.-])" + re.escape(pattern.rstrip("/")) + r"(?![\w-])", text):
                found.append(pattern)
        elif pattern.rsplit("/", 1)[-1] in text:
            found.append(pattern)
    return found


def _segments(command):
    # 구간별 (단어 목록, 쓰기 리다이렉트 대상 목록). 따옴표를 풀지 못하면 None.
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    segments, words, targets = [], [], []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _SEPARATORS:
            segments.append((words, targets))
            words, targets = [], []
        elif token in _WRITE_REDIRECTS:
            if i + 1 < len(tokens):
                targets.append(tokens[i + 1])
            i += 1
        elif token in _SKIP_NEXT:
            i += 1
        else:
            words.append(token)
        i += 1
    segments.append((words, targets))
    return segments


def _exempt(words):
    # 내용을 바꾸지 않는 구간인가. 앞쪽 변수 대입(A=1 cmd)은 건너뛴다.
    rest = list(words)
    while rest and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", rest[0]):
        rest.pop(0)
    if not rest:
        return True
    name = os.path.basename(rest[0])
    if name in _READ_ONLY:
        return True
    if name == "git":
        args = iter(rest[1:])
        for arg in args:
            if arg in _GIT_VALUE_OPTIONS:
                next(args, None)
            elif not arg.startswith("-"):
                return arg in _GIT_READ_ONLY
        return False
    for index, word in enumerate(rest):
        if word.endswith("mutation_gate.py"):
            return index + 1 < len(rest) and rest[index + 1] in _GATE_EXEMPT
    return False


def _git_args(words):
    # git 하위 명령, 그 뒤 인자, -C 경로. git 구간이 아니면 None.
    rest = list(words)
    while rest and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", rest[0]):
        rest.pop(0)
    if not rest or os.path.basename(rest[0]) != "git":
        return None
    directory = None
    args = rest[1:]
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option in _GIT_VALUE_OPTIONS and args:
            value = args.pop(0)
            if option == "-C":
                directory = value
    if not args:
        return None
    return args[0], args[1:], directory


def _tree_wide_git(words):
    # 경로 없이 작업 트리 전체를 바꾸는 git 명령이면 그 레포 경로(-C 없으면 ""), 아니면 None
    parsed = _git_args(words)
    if parsed is None:
        return None
    sub, tail, directory = parsed
    if (sub in ("apply", "am")
            or (sub == "stash" and tail[:1] in (["pop"], ["apply"]))
            or (sub == "reset" and "--hard" in tail)
            or (sub in ("checkout", "restore") and any(arg in (".", "./", ":/") for arg in tail))):
        return directory or ""
    return None


def _has_test_quality(start):
    # start 가 속한 git 레포 최상위에 .test-quality/ 가 있는가
    path = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return os.path.isdir(os.path.join(path, ".test-quality"))
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent


def command_hits(command, cwd, patterns):
    segments = _segments(command)
    if segments is None:
        return hits(command, patterns)
    # 이전 호출에서 보호 폴더로 cd 했으면 파일 이름만으로 고칠 수 있다
    in_protected_dir = bool(cwd) and bool(hits(cwd.rstrip("/") + "/", patterns))
    found = []
    for words, targets in segments:
        for target in targets:
            found += hits(target, patterns)
            if in_protected_dir and not target.startswith(("/", "~")):
                found.append(f"{cwd} 안의 {target}")
        tree_wide = _tree_wide_git(words)
        if tree_wide is not None and cwd and _has_test_quality(os.path.join(cwd, os.path.expanduser(tree_wide))):
            found.append("작업 트리 전체를 바꾸는 git 명령")
            continue
        if _exempt(words):
            continue
        for word in words:
            found += hits(word, patterns)
        if in_protected_dir:
            found.append(f"{cwd} 안에서 실행")
    return found


def touched(payload, patterns):
    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    if tool in _FILE_TOOLS:
        return hits(str(tool_input.get("file_path") or ""), patterns)
    command = tool_input.get("command")
    if not isinstance(command, str):
        return []
    if tool == "apply_patch":
        return [hit for path in _PATCH_HEADER.findall(command) for hit in hits(path.strip(), patterns)]
    if tool in _SHELL_TOOLS:
        return command_hits(command, get_cwd(payload), patterns)
    return []


def main():
    payload = read_payload()
    patterns = load_patterns()
    if not patterns:
        return
    found = sorted(set(touched(payload, patterns)))
    if not found:
        return
    reason = (
        f"변이 검사 판정을 바꾸는 파일입니다({', '.join(found)}). 판단 기록 승인·검사 범위 변경·결과는 "
        "사람이 확인합니다 — 근거와 승인자, 범위가 줄지 않았는지 보고 허락하세요."
    )
    if is_codex():
        deny(reason + " Codex는 허락 창을 띄울 수 없어 막습니다. 사용자가 직접 고치세요.")
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
