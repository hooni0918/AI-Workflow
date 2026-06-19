#!/usr/bin/env python3
import os
import shutil
import sys

from deploy_lib import compare_paths, resolve_user_path

default_roots = [
    os.path.join(os.path.expanduser("~"), "WebstormProjects", "main"),
    os.path.join(os.path.expanduser("~"), "WebstormProjects", "my-else"),
]


def main():
    roots = [resolve_user_path(root) for root in sys.argv[1:]]
    scan_roots = roots if len(roots) > 0 else default_roots

    results = []
    for root in scan_roots:
        if not exists_dir(root):
            results.append({"repo": root, "status": "skipped", "detail": "root not found"})
            continue

        if is_git_worktree(root):
            results.append(unsync_repo(root))
            continue

        for entry in sorted(os.scandir(root), key=lambda e: e.name):
            if not entry.is_dir():
                continue
            repo = os.path.join(root, entry.name)
            if not is_git_worktree(repo):
                continue
            results.append(unsync_repo(repo))

    print_results(results)


# sync_local_skills.py와 동일 규칙: local/ 하위에서 claude·codex 공통 배포 디렉토리(hooks 제외).
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


def unsync_repo(repo):
    try:
        removed = []
        deploy_dirs = local_deploy_dirs(repo)
        claude_dir = os.path.join(repo, ".claude")
        agents_dir = os.path.join(repo, ".agents")

        for name in deploy_dirs:
            source = os.path.join(repo, "local", name)
            for label, base in [(".claude", claude_dir), (".agents", agents_dir)]:
                target = os.path.join(base, name)
                if not exists_dir(target):
                    continue
                if exists_dir(source) and compare_paths(source, target):
                    shutil.rmtree(target, ignore_errors=True)
                    removed.append(f"{label}/{name}")
                else:
                    return {
                        "repo": repo,
                        "status": "skipped",
                        "detail": f"{label}/{name} differs from local/{name}",
                    }

        claude_agents = os.path.join(repo, "CLAUDE.md")
        agents_file = os.path.join(repo, "AGENTS.md")
        if is_file(agents_file):
            if is_file(claude_agents) and same_file(claude_agents, agents_file):
                _remove_file(agents_file)
                removed.append("AGENTS.md")
            else:
                return {"repo": repo, "status": "skipped", "detail": "AGENTS.md differs from CLAUDE.md"}

        gemini_file = os.path.join(repo, "GEMINI.md")
        if is_file(gemini_file):
            if is_file(claude_agents) and same_file(claude_agents, gemini_file):
                _remove_file(gemini_file)
                removed.append("GEMINI.md")
            else:
                return {"repo": repo, "status": "skipped", "detail": "GEMINI.md differs from CLAUDE.md"}

        if exists_dir(agents_dir) and len(os.listdir(agents_dir)) == 0:
            shutil.rmtree(agents_dir, ignore_errors=True)
            removed.append(".agents/")

        if len(removed) == 0:
            return {"repo": repo, "status": "skipped", "detail": "no generated local artifacts"}

        return {"repo": repo, "status": "removed", "detail": ", ".join(removed)}
    except Exception as error:
        return {"repo": repo, "status": "failed", "detail": str(error)}


def print_results(results):
    print("로컬 스킬 제거 결과")
    print("---")

    if len(results) == 0:
        print("대상 레포 없음")
        return

    for result in results:
        print(f"{short_repo(result['repo'])} | {result['status']} | {result['detail']}")

    if any(result["status"] == "failed" for result in results):
        sys.exit(1)


def short_repo(repo):
    home = os.path.expanduser("~")
    return repo[len(home) + 1:] if repo.startswith(home) else repo


def is_git_worktree(repo):
    return os.path.exists(os.path.join(repo, ".git"))


def exists_dir(target):
    return os.path.exists(target) and os.path.isdir(target)


def is_file(target):
    return os.path.exists(target) and os.path.isfile(target)


def same_file(left, right):
    with open(left, "rb") as lf, open(right, "rb") as rf:
        return lf.read() == rf.read()


def _remove_file(target):
    try:
        os.remove(target)
    except FileNotFoundError:
        pass


# 다른 모듈에서 import할 때 쓰는 공개 이름.
unsync_local_skills = main


if __name__ == "__main__":
    main()
