# 로컬판 settings/hooks 배포 라이브러리.
#
# 전역 배포(deploy/ → ~/.claude·~/.codex)와 **동일한 메커니즘**을 repo-local 산출물
# (.claude/settings.json·.codex/hooks.json)에 적용한다. 소스는 local/(전역 deploy/의
# 로컬판). settings.json은 통째 덮어쓰지 않고 deploy_lib의 부분키 머지(merge_settings,
# .ac-keys 매니페스트)를 그대로 재사용한다. 분기점은 settings_projection의 LOCAL_ADAPTERS
# (repo-relative command, codex run_command+Bash 매처)뿐이다.
import os

from settings_projection import build_hooks, LOCAL_ADAPTERS, local_hook_command
from deploy_lib import (
    copy_path,
    ensure_dir,
    merge_settings,
    read_json,
    remove_path,
    repo_dir,
    settings_manifest_path,
    split_settings,
    write_json,
)

local_source_dir = os.path.join(repo_dir, "local")
local_base_settings_source = os.path.join(local_source_dir, "base-settings.json")

# 로컬 타겟(repo-local).
local_claude_dir = os.path.join(repo_dir, ".claude")
local_codex_dir = os.path.join(repo_dir, ".codex")
local_claude_settings_path = os.path.join(local_claude_dir, "settings.json")
local_codex_hooks_path = os.path.join(local_codex_dir, "hooks.json")
local_hooks_source = os.path.join(local_source_dir, "hooks")
local_claude_hooks_dir = os.path.join(local_claude_dir, "hooks")
local_codex_hooks_dir = os.path.join(local_codex_dir, "hooks")

build_opts = {"adapters": LOCAL_ADAPTERS, "makeCommand": local_hook_command}


def load_local_base_settings():
    if not (
        os.path.exists(local_base_settings_source) and os.path.isfile(local_base_settings_source)
    ):
        raise RuntimeError(f"local/base-settings.json을 찾을 수 없습니다: {local_base_settings_source}")
    return read_json(local_base_settings_source)


def load_local_override(name):
    override_path = os.path.join(local_source_dir, name)
    if os.path.exists(override_path) and os.path.isfile(override_path):
        return read_json(override_path)
    return {}


# .claude/settings.json에 부분 머지될 객체(hooks + claude 전용 override).
def local_claude_settings_object():
    result = {"hooks": build_hooks(load_local_base_settings()["hooks"], "claude", build_opts)}
    result.update(load_local_override("claude-settings.json"))
    return result


# .codex/hooks.json에 whole-file로 쓰일 객체(codex는 override 없이 hook만).
def local_codex_hooks_object():
    return {"hooks": build_hooks(load_local_base_settings()["hooks"], "codex", build_opts)}


# local/hooks/*.py를 .claude/hooks/·.codex/hooks/로 복사한다. 복사 전 AC 생성 디렉토리를
# 제거해 소스에서 사라진 hook(고아)이 잔존하지 않게 한다(전역의 uninstall-후-배포와 동일).
def copy_local_hooks(log=print):
    if not (os.path.exists(local_hooks_source) and os.path.isdir(local_hooks_source)):
        raise RuntimeError(f"local/hooks/를 찾을 수 없습니다: {local_hooks_source}")
    for target_dir, hooks_dir in [
        (local_claude_dir, local_claude_hooks_dir),
        (local_codex_dir, local_codex_hooks_dir),
    ]:
        ensure_dir(target_dir)
        remove_path(hooks_dir)
        copy_path(local_hooks_source, hooks_dir)
        log(f"  COPY  {os.path.relpath(hooks_dir, repo_dir).replace(os.sep, '/')}")


# AC가 생성한 로컬 산출물만 제거한다. .claude/settings.json은 split_settings로 AC 키만
# 부분 제거(사용자 키 보존), codex hooks.json·hooks 디렉토리는 AC 전유라 통째 제거.
def uninstall_local(log=print):
    removed = 0

    if split_settings(local_claude_settings_object(), local_claude_settings_path):
        log("  SPLIT .claude/settings.json")
        removed += 1
    if os.path.exists(local_claude_hooks_dir):
        remove_path(local_claude_hooks_dir)
        log("  DEL   .claude/hooks/")
        removed += 1
    if os.path.exists(local_codex_hooks_path):
        remove_path(local_codex_hooks_path)
        log("  DEL   .codex/hooks.json")
        removed += 1
    if os.path.exists(local_codex_hooks_dir):
        remove_path(local_codex_hooks_dir)
        log("  DEL   .codex/hooks/")
        removed += 1
    return removed
