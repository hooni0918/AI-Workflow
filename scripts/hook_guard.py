# git hook 준비 상태 가드.
#
# commit-msg 훅을 scripts/commit_msg.py로 연결한다(make install-hooks). 준비 상태 = commit-msg 훅이 commit_msg.py를
# 가리키도록 설치돼 있는지로 정의한다. 복구는 `make install-hooks`로 시도한다.
import os
import subprocess

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def in_git_repo():
    return bool(read_git_dir()) or bool(read_git_config("core.hooksPath"))


def ensure_hooks_ready():
    # git 레포 밖에서는 commit-msg 훅을 설치할 곳이 없다. 배포(sync) 자체는 git과
    # 무관하므로, 레포가 아니면 경고만 남기고 통과시킨다(하드 실패 금지).
    if not in_git_repo():
        print("git 레포가 아니므로 commit-msg 훅 설치를 건너뜁니다 (배포는 계속).")
        return

    state = check_hooks()

    if not state["ok"] and state["repairable"]:
        print("AC git hook 준비 상태가 불완전합니다. make install-hooks로 복구를 시도합니다.")
        run_prepare()
        state = check_hooks()

    if state["ok"]:
        return

    lines = [
        "AC git hook 준비 상태가 올바르지 않습니다.",
        *[f"- {issue}" for issue in state["issues"]],
        "",
        "하네스로 만든 worktree는 self-heal hook이 의존성을 자동 설치합니다. "
        "자동 복구가 안 됐다면 이 worktree에서 make install-hooks를 실행하세요.",
    ]
    raise RuntimeError("\n".join(lines))


def check_hooks():
    issues = []
    repairable = False

    commit_msg_hook = commit_msg_target()
    if commit_msg_hook is None:
        issues.append("commit-msg 훅이 설치되지 않음 (core.hooksPath/.git/hooks 모두 없음)")
        repairable = has_commit_msg_source()
    elif not is_file(commit_msg_hook):
        issues.append(f"commit-msg 훅 파일이 없음: {commit_msg_hook}")
        repairable = has_commit_msg_source()
    elif not hook_points_to_source(commit_msg_hook):
        issues.append(f"commit-msg 훅이 commit_msg.py를 가리키지 않음: {commit_msg_hook}")
        repairable = has_commit_msg_source()

    if not has_commit_msg_source():
        issues.append(f"commit_msg.py 소스가 없음: {commit_msg_source()}")

    return {"ok": len(issues) == 0, "issues": issues, "repairable": repairable}


# core.hooksPath가 설정돼 있으면 그 디렉토리, 아니면 .git/hooks의 commit-msg 경로.
# .git이 worktree gitdir 파일인 경우(commondir)는 git이 직접 알려준 hooksPath를 쓴다.
def commit_msg_target():
    hooks_path = read_git_config("core.hooksPath")
    if hooks_path:
        base = hooks_path if os.path.isabs(hooks_path) else os.path.join(repo_root, hooks_path)
        return os.path.join(base, "commit-msg")

    git_dir = read_git_dir()
    if not git_dir:
        return None
    return os.path.join(git_dir, "hooks", "commit-msg")


def hook_points_to_source(hook_path):
    try:
        with open(hook_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except Exception:
        return False
    return "commit_msg.py" in content


def read_git_dir():
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return ""
    git_dir = result.stdout.strip()
    if not git_dir:
        return ""
    return git_dir if os.path.isabs(git_dir) else os.path.join(repo_root, git_dir)


def read_git_config(key):
    result = subprocess.run(
        ["git", "config", "--get", key],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        encoding="utf-8",
    )

    if result.returncode == 1:
        return ""

    if result.returncode != 0:
        message = (result.stderr or f"git config {key} 실패").strip()
        raise RuntimeError(message)

    return result.stdout.strip()


def run_prepare():
    result = subprocess.run(
        ["make", "install-hooks"],
        cwd=repo_root,
    )

    if result.returncode != 0:
        raise RuntimeError("make install-hooks 실패")


def commit_msg_source():
    return os.path.join(repo_root, "scripts", "commit_msg.py")


def has_commit_msg_source():
    return is_file(commit_msg_source())


def is_file(file):
    return os.path.exists(file) and os.path.isfile(file)
