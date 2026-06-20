#!/usr/bin/env python3
import os
import sys

from hook_guard import ensure_hooks_ready
from deploy_lib import copy_path, ensure_dir, resolve_user_path

# 스캔 대상 프로젝트 루트는 인자로 명시하거나 AC_SKILL_ROOTS 환경변수(구분자 os.pathsep)로 지정한다.
default_roots = [p for p in os.environ.get("AC_SKILL_ROOTS", "").split(os.pathsep) if p]


def main(opts=None):
    opts = opts or {}
    if opts.get("ensureHooks") is not False:
        ensure_hooks_ready()

    roots = [resolve_user_path(root) for root in sys.argv[1:]]
    scan_roots = roots if len(roots) > 0 else default_roots

    results = []
    for root in scan_roots:
        if not exists_dir(root):
            results.append({"repo": root, "status": "skipped", "detail": "root not found"})
            continue

        if is_git_worktree(root):
            results.append(sync_repo(root))
            continue

        for entry in sorted(os.scandir(root), key=lambda e: e.name):
            if not entry.is_dir():
                continue
            repo = os.path.join(root, entry.name)
            if not is_git_worktree(repo):
                continue
            results.append(sync_repo(repo))

    print_results(results)

    if any(result["status"] == "failed" for result in results):
        sys.exit(1)


# local/ 하위에서 claude·codex 공통으로 배포하는 디렉토리. hooks는 settings projection이
# .claude/hooks·.codex/hooks로 따로 투영하므로 제외한다(settings/.json 파일은 디렉토리가 아니라 자연 제외).
LOCAL_DEPLOY_EXCLUDE = {"hooks"}


def local_deploy_dirs(repo):
    local_dir = os.path.join(repo, "local")
    if not exists_dir(local_dir):
        return []
    return sorted(
        entry.name
        for entry in os.scandir(local_dir)
        if entry.is_dir() and entry.name not in LOCAL_DEPLOY_EXCLUDE
    )


def sync_repo(repo):
    deploy_dirs = local_deploy_dirs(repo)
    claude_agents = resolve_claude_agents(repo)
    has_agents = claude_agents is not None

    if len(deploy_dirs) == 0 and not has_agents:
        return {"repo": repo, "status": "skipped", "detail": "no local/ deploy dirs or CLAUDE.md"}

    try:
        synced = []
        claude_dir = os.path.join(repo, ".claude")
        agents_dir = os.path.join(repo, ".agents")
        for name in deploy_dirs:
            source = os.path.join(repo, "local", name)
            ensure_dir(claude_dir)
            ensure_dir(agents_dir)
            copy_path(source, os.path.join(claude_dir, name))
            copy_path(source, os.path.join(agents_dir, name))
            synced.append(f"local/{name} -> .claude/{name}, .agents/{name}")
        if has_agents:
            copy_path(claude_agents, os.path.join(repo, "AGENTS.md"))
            copy_path(claude_agents, os.path.join(repo, "GEMINI.md"))
            synced.append(f"{short_source(repo, claude_agents)} -> AGENTS.md, GEMINI.md")
        return {"repo": repo, "status": "synced", "detail": ", ".join(synced)}
    except Exception as error:
        return {"repo": repo, "status": "failed", "detail": str(error)}


def print_results(results):
    print("로컬 스킬 동기화 결과")
    print("---")

    if len(results) == 0:
        print("대상 레포 없음")
        return

    for result in results:
        print(f"{short_repo(result['repo'])} | {result['status']} | {result['detail']}")


def short_repo(repo):
    home = os.path.expanduser("~")
    return repo[len(home) + 1:] if repo.startswith(home) else repo


def is_git_worktree(repo):
    return os.path.exists(os.path.join(repo, ".git"))


def exists_dir(target):
    return os.path.exists(target) and os.path.isdir(target)


def resolve_claude_agents(repo):
    candidate = os.path.join(repo, "CLAUDE.md")
    if os.path.exists(candidate) and os.path.isfile(candidate):
        return candidate
    return None


def short_source(repo, file):
    return os.path.relpath(file, repo).replace(os.sep, "/")


# 다른 모듈에서 import할 때 쓰는 공개 이름.
sync_local_skills = main


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        sys.stderr.write(f"{error}\n")
        sys.exit(1)
