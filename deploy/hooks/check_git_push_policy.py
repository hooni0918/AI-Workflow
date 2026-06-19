#!/usr/bin/env python3
"""git push 정책 훅.

보호 브랜치 push 차단, open PR 존재 시 차단, force push 검증,
history rewrite + force push chain 차단.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import deny, get_command, read_payload  # noqa: E402

_FORCE_RE = re.compile(r"^(--force|--force-with-lease|-f)$|^--force-with-lease=")
_PROTECTED_BRANCHES = re.compile(r"^(master|main|develop|release)$")


def tokenize(value):
    tokens = []
    pattern = re.compile(r'"([^"]*)"|\'([^\']*)\'|(\S+)')
    for match in pattern.finditer(value):
        # JS: match[1] || match[2] || match[3]
        tokens.append(match.group(1) or match.group(2) or match.group(3))
    return tokens


def split_segments(command):
    out = []
    buf = ""
    quote = None
    i = 0
    n = len(command)
    while i < n:
        c = command[i]
        if quote:
            if c == quote:
                quote = None
            buf += c
            i += 1
            continue
        if c == '"' or c == "'":
            quote = c
            buf += c
            i += 1
            continue
        if c == ";" or c == "\n":
            out.append(buf)
            buf = ""
            i += 1
            continue
        nxt = command[i + 1] if i + 1 < n else None
        if (c == "&" and nxt == "&") or (c == "|" and nxt == "|"):
            out.append(buf)
            buf = ""
            i += 2
            continue
        if c == "|":
            out.append(buf)
            buf = ""
            i += 1
            continue
        buf += c
        i += 1
    if buf:
        out.append(buf)
    return out


def parse_git_invocation(tokens, start_idx):
    i = start_idx
    cwd = None
    while i < len(tokens):
        t = tokens[i]
        if t is None:
            i += 1
            continue
        if t == "-C":
            if i + 1 < len(tokens) and tokens[i + 1]:
                cwd = tokens[i + 1]
            i += 2
            continue
        if t == "-c":
            i += 2
            continue
        if t in ("--git-dir", "--work-tree", "--namespace", "--super-prefix", "--exec-path"):
            i += 2
            continue
        if t.startswith("--") and "=" in t:
            i += 1
            continue
        if t.startswith("-"):
            i += 1
            continue
        return {"subcommand": t, "args": tokens[i + 1:], "cwd": cwd}
    return None


def find_git_invocations(command, subcommand):
    out = []
    for seg in split_segments(command):
        tokens = tokenize(seg)
        for i in range(len(tokens)):
            if tokens[i] != "git":
                continue
            parsed = parse_git_invocation(tokens, i + 1)
            if parsed and parsed["subcommand"] == subcommand:
                out.append({"args": parsed["args"], "cwd": parsed["cwd"]})
            break
    return out


def is_history_rewrite(parsed):
    subcommand = parsed["subcommand"]
    args = parsed["args"]
    if subcommand in ("rebase", "cherry-pick"):
        return True
    if subcommand == "reset":
        return any(re.match(r"^--(soft|mixed|hard|keep|merge)$", t) for t in args)
    if subcommand == "commit":
        return any(t == "--amend" for t in args)
    return False


def find_history_rewrites(command):
    out = []
    for seg in split_segments(command):
        tokens = tokenize(seg)
        for i in range(len(tokens)):
            if tokens[i] != "git":
                continue
            parsed = parse_git_invocation(tokens, i + 1)
            if parsed and is_history_rewrite(parsed):
                out.append(parsed)
            break
    return out


def extract_push_target_branch(args):
    positional = []
    for token in args:
        if not token:
            continue
        if token.startswith("-"):
            continue
        positional.append(token)

    if len(positional) < 2:
        return None
    refspec = positional[1]
    if not refspec:
        return None

    branch = refspec.split(":")[-1] if ":" in refspec else refspec
    if not branch or branch == "HEAD":
        return None
    return re.sub(r"^refs/heads/", "", branch)


def normalize_cwd(value):
    if not value:
        return None
    c = value
    # subprocess는 ~를 expand하지 않음. 미해석 cwd면 ENOENT로 hook이 우회됨.
    if c.startswith("~"):
        c = re.sub(r"^~(?=$|[/\\])", os.path.expanduser("~"), c)
    # Windows MSYS/Git Bash 경로(/c/foo) -> C:\foo
    if sys.platform == "win32":
        msys = re.match(r"^/([a-zA-Z])(/|$)", c)
        if msys:
            c = msys.group(1).upper() + ":\\" + c[3:].replace("/", "\\")
    return os.path.normpath(c)


def _git(args, cwd=None, quiet=False):
    """git 실행. 성공 시 stdout(str) 반환, 실패 시 예외. JS execSync 대응."""
    kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if cwd:
        kwargs["cwd"] = cwd
    result = subprocess.run(args, **kwargs)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)
    return result.stdout.decode("utf-8", "replace")


def main():
    cmd = get_command(read_payload())
    if not isinstance(cmd, str):
        sys.exit(0)

    push_invocations = find_git_invocations(cmd, "push")
    if len(push_invocations) == 0:
        sys.exit(0)

    # chained 우회 차단: history rewrite + force push를 한 명령에 chain하면
    # PreToolUse hook은 rewrite 실행 전 상태로 1회만 검사한다.
    force_push_present = any(
        any(_FORCE_RE.search(t) for t in inv["args"]) for inv in push_invocations
    )
    if force_push_present and len(find_history_rewrites(cmd)) > 0:
        deny(
            "history rewrite(reset --soft/--mixed/--hard, rebase, cherry-pick, commit --amend)와 force push를 한 명령으로 chain하면 훅이 push 시점 상태를 검증하지 못합니다. 두 명령을 분리해 각각 실행하세요 (rewrite 먼저 → 그다음 force push)."
        )

    cd_match = re.search(
        r"(?:^|[;&|])\s*cd\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|]+))", cmd
    )
    cd_cwd = None
    if cd_match:
        cd_cwd = cd_match.group(1) or cd_match.group(2) or cd_match.group(3)
    cd_cwd = normalize_cwd(cd_cwd)

    for inv in push_invocations:
        if "--no-verify" in inv["args"]:
            deny("--no-verify 금지. pre-push hook을 우회하지 마세요.")

        # git -C <path>가 우선. 없으면 cd 추출 cwd로 fallback.
        inv_cwd = normalize_cwd(inv["cwd"]) or cd_cwd

        explicit_target = extract_push_target_branch(inv["args"])

        if explicit_target and _PROTECTED_BRANCHES.search(explicit_target):
            deny(f"{explicit_target} 브랜치에 push 금지.")

        try:
            branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=inv_cwd).strip()
        except Exception as e:
            # execSync throw 시 deny가 호출되지 못해 보호 브랜치 검증 우회.
            cwd_display = inv_cwd if inv_cwd is not None else "<inherit>"
            deny(f"Hook이 브랜치를 확인할 수 없습니다 (cwd={cwd_display}): {e}")

        target_branch = explicit_target or branch

        if _PROTECTED_BRANCHES.search(target_branch):
            deny(f"{target_branch} 브랜치에 push 금지.")

        try:
            pr_state = _git(
                ["gh", "pr", "view", target_branch, "--json", "state", "-q", ".state"],
                cwd=inv_cwd,
            ).strip()
            if pr_state == "OPEN":
                deny(
                    f"{target_branch} 브랜치에 열린 PR이 있습니다. AI는 푸시하지 않습니다 — 사용자가 직접 푸시하세요."
                )
        except Exception:
            # No PR, gh unavailable, or no GitHub remote. Continue with local checks.
            pass

        if any(_FORCE_RE.search(t) for t in inv["args"]):
            try:
                _git(["git", "fetch", "origin", branch], cwd=inv_cwd)
            except Exception:
                continue

            try:
                _git(
                    ["git", "diff", f"origin/{branch}", "HEAD", "--quiet"], cwd=inv_cwd
                )
            except Exception:
                deny(
                    f"force push 차단: origin/{branch}과 코드가 다릅니다. 히스토리 정리(squash, reword)만 허용됩니다."
                )


if __name__ == "__main__":
    main()
