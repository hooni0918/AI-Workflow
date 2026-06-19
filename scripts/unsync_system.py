#!/usr/bin/env python3
import sys

from deploy_lib import (
    default_codex_dir,
    default_claude_dir,
    default_gemini_dir,
    ensure_deploy_source,
    resolve_user_path,
    uninstall_codex_globals,
    uninstall_gemini_globals,
    uninstall_target,
)


def main():
    ensure_deploy_source()

    explicit_target = sys.argv[1] if len(sys.argv) > 1 else None
    target_arg = explicit_target or ask_target()
    target_dir = resolve_user_path(target_arg or default_claude_dir())

    print(f"타겟: {target_dir}")
    print("---")

    removed = uninstall_target(target_dir)

    if not explicit_target and target_dir == default_claude_dir():
        codex_target_dir = default_codex_dir()
        print("")
        print(f"Codex 타겟: {codex_target_dir}")
        print("---")
        removed += uninstall_codex_globals(codex_target_dir)

        gemini_target_dir = default_gemini_dir()
        print("")
        print(f"Gemini 타겟: {gemini_target_dir}")
        print("---")
        removed += uninstall_gemini_globals(gemini_target_dir)

    print("---")
    print(f"완료: {removed}개 제거")


def ask_target():
    default_target = default_claude_dir()
    try:
        answer = input(f"타겟 경로 [{default_target}]: ")
    except EOFError:
        answer = ""
    return answer.strip() or default_target


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        sys.stderr.write(f"{error}\n")
        sys.exit(1)
