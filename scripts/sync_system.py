#!/usr/bin/env python3
import os
import subprocess
import sys

from hook_guard import ensure_hooks_ready
from deploy_lib import (
    CATEGORIES,
    SOURCE_ONLY_ROOT_FILES,
    build_codex_agents_content,
    build_gemini_agents_content,
    claude_settings_object,
    codex_hooks_object,
    gemini_settings_object,
    compare_paths,
    copy_path,
    default_codex_dir,
    default_claude_dir,
    default_gemini_dir,
    deploy_codex_globals,
    deploy_gemini_globals,
    deploy_root_files,
    deploy_skills,
    ensure_deploy_source,
    ensure_dir,
    list_entries,
    unset_wt_add_alias,
    resolve_user_path,
    source_dir,
    trust_codex_hooks,
    uninstall_target,
    verify_json_exact,
    verify_settings,
)

_script_dir = os.path.dirname(os.path.abspath(__file__))


def main():
    ensure_hooks_ready()
    ensure_deploy_source()
    # base-settings.json 생성 계약이 깨지면 배포 전에 중단(fail-fast).
    subprocess.run(
        [sys.executable, os.path.join(_script_dir, "verify_settings_projection.py")],
        check=True,
    )

    target_arg = sys.argv[1] if len(sys.argv) > 1 else None
    target_dir = resolve_user_path(target_arg or default_claude_dir())
    print(f"소스: {source_dir}")
    print(f"타겟: {target_dir}")
    print("---")

    ensure_dir(target_dir)

    print("기존 파일 제거 중...")
    uninstall_target(target_dir, {"removeAlias": False})
    print("")

    copied = 0

    for category in CATEGORIES:
        src = os.path.join(source_dir, category)
        if not exists_dir(src):
            continue

        copy_path(src, os.path.join(target_dir, category))
        print(f"  COPY  {category}/")
        copied += 1

    copied += deploy_skills(target_dir, print)

    print("---")
    print(f"복사 완료: {copied}개")
    print("")

    copied += deploy_root_files(target_dir, print)

    print("검증 중...")
    failures = []

    for category in CATEGORIES:
        src = os.path.join(source_dir, category)
        if not exists_dir(src):
            continue

        target = os.path.join(target_dir, category)
        if not exists_dir(target):
            fail(failures, f"{category}/ 존재하지 않음")
        elif compare_paths(src, target):
            print(f"  PASS  {category}/")
        else:
            fail(failures, f"{category}/ 내용 불일치")

    src_skills = os.path.join(source_dir, "skills")
    if exists_dir(src_skills):
        for entry in list_entries(src_skills):
            src = os.path.join(src_skills, entry.name)
            target = os.path.join(target_dir, "skills", entry.name)
            if not path_exists(target):
                fail(failures, f"skills/{entry.name} 존재하지 않음")
            elif compare_paths(src, target):
                print(f"  PASS  skills/{entry.name}")
            else:
                fail(failures, f"skills/{entry.name} 내용 불일치")

    for entry in list_entries(source_dir):
        if not entry.is_file():
            continue
        if entry.name in SOURCE_ONLY_ROOT_FILES:
            continue

        src = os.path.join(source_dir, entry.name)
        target = os.path.join(target_dir, entry.name)
        if not path_exists(target):
            fail(failures, f"{entry.name} 존재하지 않음")
        elif compare_paths(src, target):
            print(f"  PASS  {entry.name}")
        else:
            fail(failures, f"{entry.name} 내용 불일치")

    target_settings = os.path.join(target_dir, "settings.json")
    if not path_exists(target_settings):
        fail(failures, "settings.json 존재하지 않음")
    elif verify_settings(claude_settings_object(), target_settings):
        print("  PASS  settings.json (merged)")
    else:
        fail(failures, "settings.json 머지 결과 키 불일치")

    print("---")
    if len(failures) > 0:
        sys.stderr.write(f"검증 실패: {len(failures)}개 항목 확인 필요\n")
        sys.exit(1)
    print("검증 완료: 모두 정상")

    print("")
    print("---")
    print("구버전 git wt-add alias 정리 중 (워크트리 복구는 self-heal hook이 전담)...")
    unset_wt_add_alias(print)

    if not target_arg:
        print("")
        print("---")
        codex_target_dir = default_codex_dir()
        print(f"Codex 전역 자산 배포 중: {codex_target_dir}")
        codex_copied = deploy_codex_globals(codex_target_dir, print)
        print(f"Codex 배포 완료: {codex_copied}개")
        try:
            trust_codex_hooks(codex_target_dir, print)
        except Exception as error:
            if not is_recoverable_codex_trust_error(error):
                raise
            print(f"  WARN  Codex hook trust 건너뜀: {_message(error)}")
            print(
                "  WARN  Codex Desktop이 CLI를 외부에서 실행할 수 없는 환경입니다. "
                "배포 자산은 정상 복사되었고, hook trust는 Desktop에서 다시 확인하면 됩니다."
            )
        verify_codex_globals(codex_target_dir)

        print("")
        print("---")
        gemini_target_dir = default_gemini_dir()
        print(f"Gemini 전역 자산 배포 중: {gemini_target_dir}")
        gemini_copied = deploy_gemini_globals(gemini_target_dir, print)
        print(f"Gemini 배포 완료: {gemini_copied}개")
        verify_gemini_globals(gemini_target_dir)


def is_recoverable_codex_trust_error(error):
    message = _message(error)
    return any(
        pattern in message
        for pattern in [
            "Codex CLI not found",
            "Access is denied",
            "spawn EPERM",
            "spawn UNKNOWN",
            "spawn EACCES",
            "spawn ENOENT",
        ]
    )


def verify_codex_globals(target_dir):
    print("")
    print("Codex 검증 중...")
    failures = []

    src_contexts = os.path.join(source_dir, "contexts")
    target_contexts = os.path.join(target_dir, "contexts")
    if not exists_dir(target_contexts):
        fail(failures, "codex contexts/ 존재하지 않음")
    elif compare_paths(src_contexts, target_contexts):
        print("  PASS  codex contexts/")
    else:
        fail(failures, "codex contexts/ 내용 불일치")

    src_skills = os.path.join(source_dir, "skills")
    if exists_dir(src_skills):
        for entry in list_entries(src_skills):
            src = os.path.join(src_skills, entry.name)
            target = os.path.join(target_dir, "skills", entry.name)
            if not path_exists(target):
                fail(failures, f"codex skills/{entry.name} 존재하지 않음")
            elif compare_paths(src, target):
                print(f"  PASS  codex skills/{entry.name}")
            else:
                fail(failures, f"codex skills/{entry.name} 내용 불일치")

    src_hooks = os.path.join(source_dir, "hooks")
    target_hooks = os.path.join(target_dir, "hooks")
    if exists_dir(src_hooks):
        if not exists_dir(target_hooks):
            fail(failures, "codex hooks/ 존재하지 않음")
        elif compare_paths(src_hooks, target_hooks):
            print("  PASS  codex hooks/")
        else:
            fail(failures, "codex hooks/ 내용 불일치")

    target_hooks_config = os.path.join(target_dir, "hooks.json")
    if not path_exists(target_hooks_config):
        fail(failures, "codex hooks.json 존재하지 않음")
    elif verify_json_exact(codex_hooks_object(), target_hooks_config):
        print("  PASS  codex hooks.json")
    else:
        fail(failures, "codex hooks.json 내용 불일치")

    target_agents = os.path.join(target_dir, "AGENTS.md")
    if not path_exists(target_agents):
        fail(failures, "codex AGENTS.md 존재하지 않음")
    else:
        with open(target_agents, "r", encoding="utf-8") as handle:
            if handle.read() == build_codex_agents_content():
                print("  PASS  codex AGENTS.md")
            else:
                fail(failures, "codex AGENTS.md 내용 불일치")

    if len(failures) > 0:
        sys.stderr.write(f"Codex 검증 실패: {len(failures)}개 항목 확인 필요\n")
        sys.exit(1)
    print("Codex 검증 완료: 모두 정상")


def verify_gemini_globals(target_dir):
    print("")
    print("Gemini 검증 중...")
    failures = []

    src_contexts = os.path.join(source_dir, "contexts")
    target_contexts = os.path.join(target_dir, "contexts")
    if not exists_dir(target_contexts):
        fail(failures, "gemini contexts/ 존재하지 않음")
    elif compare_paths(src_contexts, target_contexts):
        print("  PASS  gemini contexts/")
    else:
        fail(failures, "gemini contexts/ 내용 불일치")

    src_skills = os.path.join(source_dir, "skills")
    if exists_dir(src_skills):
        for entry in list_entries(src_skills):
            src = os.path.join(src_skills, entry.name)
            target = os.path.join(target_dir, "skills", entry.name)
            if not path_exists(target):
                fail(failures, f"gemini skills/{entry.name} 존재하지 않음")
            elif compare_paths(src, target):
                print(f"  PASS  gemini skills/{entry.name}")
            else:
                fail(failures, f"gemini skills/{entry.name} 내용 불일치")

    target_settings = os.path.join(target_dir, "settings.json")
    if not path_exists(target_settings):
        fail(failures, "gemini settings.json 존재하지 않음")
    elif verify_settings(gemini_settings_object(), target_settings):
        print("  PASS  gemini settings.json (merged)")
    else:
        fail(failures, "gemini settings.json 머지 결과 키 불일치")

    target_agents = os.path.join(target_dir, "GEMINI.md")
    if not path_exists(target_agents):
        fail(failures, "gemini GEMINI.md 존재하지 않음")
    else:
        with open(target_agents, "r", encoding="utf-8") as handle:
            if handle.read() == build_gemini_agents_content():
                print("  PASS  gemini GEMINI.md")
            else:
                fail(failures, "gemini GEMINI.md 내용 불일치")

    if len(failures) > 0:
        sys.stderr.write(f"Gemini 검증 실패: {len(failures)}개 항목 확인 필요\n")
        sys.exit(1)
    print("Gemini 검증 완료: 모두 정상")


def fail(failures, message):
    failures.append(message)
    print(f"  FAIL  {message}")


def path_exists(target):
    return os.path.exists(target)


def exists_dir(target):
    return os.path.exists(target) and os.path.isdir(target)


def _message(error):
    return str(error)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:
        sys.stderr.write(f"{_message(error)}\n")
        sys.exit(1)
