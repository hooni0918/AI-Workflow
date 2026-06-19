#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys

from environment_lib import (
    remove_managed_blocks,
    remove_if_identical,
    query_reg_value,
    delete_reg_value,
    runs,
)

home = os.path.expanduser("~")
state_dir = os.path.join(home, ".ai-workflow")
state_file = os.path.join(state_dir, "environment-state.json")
global_gitignore = os.path.join(home, ".gitignore_global")
cmd_autorun_file = os.path.join(home, "autorun.cmd")
cmd_processor_key = "HKCU\\Software\\Microsoft\\Command Processor"

cmd_autorun_body = """@echo off
echo %CMDCMDLINE% | findstr /i " /c " >nul
if errorlevel 1 (
    if /i "%CD%"=="%USERPROFILE%" cd /d %USERPROFILE%\\WebstormProjects\\main
)
"""


def main():
    state = read_state()

    print("--- PowerShell ---")
    unsync_power_shell(state)

    print("--- Global gitignore ---")
    unsync_global_gitignore(state)

    print("--- cmd autorun ---")
    unsync_cmd_autorun(state)

    if state.get("powerShell7InstalledByAiContexts"):
        uninstall_power_shell7(state)

    write_state(state)
    print("Environment unsync complete.")


def unsync_power_shell(state=None):
    if sys.platform != "win32":
        print("Skipping PowerShell setup removal because this is not Windows.")
        return

    pwsh = find_power_shell7_command()
    for profile in dict.fromkeys(get_power_shell_profiles(pwsh)):
        remove_managed_blocks(
            profile,
            [
                re.compile(
                    r"# >>> ai-workflow powershell utf8 >>>[\s\S]*?"
                    r"# <<< ai-workflow powershell utf8 <<<\r?\n?"
                ),
                re.compile(
                    r"# >>> ai-workflow utf8 >>>[\s\S]*?# <<< ai-workflow utf8 <<<\r?\n?"
                ),
                re.compile(
                    r"# >>> test-playground powershell utf8 >>>[\s\S]*?"
                    r"# <<< test-playground powershell utf8 <<<\r?\n?"
                ),
            ],
        )


def unsync_global_gitignore(state):
    remove_managed_blocks(
        global_gitignore,
        [
            re.compile(
                r"# >>> ai-workflow global gitignore >>>[\s\S]*?"
                r"# <<< ai-workflow global gitignore <<<\r?\n?"
            )
        ],
    )

    if not state.get("gitCoreExcludesFileSetByAiContexts"):
        return

    current_path = get_global_git_excludes_file()
    if os.path.abspath(current_path or "") == os.path.abspath(global_gitignore):
        subprocess.run(
            ["git", "config", "--global", "--unset", "core.excludesFile"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            check=True,
        )
        print("Removed global core.excludesFile registration")
    state.pop("gitCoreExcludesFileSetByAiContexts", None)


def unsync_cmd_autorun(state):
    if sys.platform != "win32":
        print("Skipping cmd autorun removal because this is not Windows.")
        return

    if state.get("cmdAutorunRegSetByAiContexts"):
        current = query_reg_value(cmd_processor_key, "AutoRun")
        if current == f"@{cmd_autorun_file}":
            delete_reg_value(cmd_processor_key, "AutoRun")
            print("Removed AutoRun registration")
        else:
            print(f"AutoRun changed since sync ({current or 'absent'}); leaving as is")
        state.pop("cmdAutorunRegSetByAiContexts", None)

    status = remove_if_identical(cmd_autorun_file, cmd_autorun_body)
    print(
        {
            "removed": f"Removed {cmd_autorun_file}",
            "modified": f"Modified outside ai-workflow; leaving {cmd_autorun_file}",
            "absent": f"Already absent: {cmd_autorun_file}",
        }[status]
    )


def uninstall_power_shell7(state):
    if not runs("winget", ["--version"]):
        sys.stderr.write("winget was not found. Skipping PowerShell 7 uninstall.\n")
        return

    try:
        subprocess.run(
            [
                "winget",
                "uninstall",
                "--exact",
                "--id",
                "Microsoft.PowerShell",
                "--source",
                "winget",
                "--accept-source-agreements",
            ],
            check=True,
        )
        state.pop("powerShell7InstalledByAiContexts", None)
    except Exception as error:
        sys.stderr.write(f"PowerShell 7 uninstall skipped or failed: {error}\n")


def find_power_shell7_command():
    local_app_data = os.environ.get("LOCALAPPDATA")
    candidates = [
        c
        for c in [
            "pwsh",
            local_app_data
            and os.path.join(local_app_data, "Microsoft", "WindowsApps", "pwsh.exe"),
            os.environ.get("ProgramFiles")
            and os.path.join(os.environ["ProgramFiles"], "PowerShell", "7", "pwsh.exe"),
        ]
        if c
    ]

    return next((c for c in candidates if runs(c, ["--version"])), None)


def get_power_shell_profiles(pwsh):
    return [
        get_power_shell_profile(
            "powershell",
            os.path.join(
                home, "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1"
            ),
        ),
        get_power_shell_profile(
            pwsh or "pwsh",
            os.path.join(home, "Documents", "PowerShell", "Microsoft.PowerShell_profile.ps1"),
        ),
    ]


def get_power_shell_profile(command, fallback):
    try:
        profile = subprocess.run(
            [command, "-NoProfile", "-Command", "$PROFILE"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            check=True,
        ).stdout.strip()
        return profile or fallback
    except Exception:
        return fallback


def get_global_git_excludes_file():
    try:
        return subprocess.run(
            ["git", "config", "--global", "--get", "core.excludesFile"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            check=True,
        ).stdout.strip()
    except Exception:
        return ""


def read_state():
    if not os.path.exists(state_file):
        return {}
    try:
        with open(state_file, "r", encoding="utf-8") as handle:
            return json.loads(handle.read())
    except Exception:
        return {}


def write_state(state):
    keys = list(state.keys())
    if len(keys) == 0:
        try:
            os.remove(state_file)
        except FileNotFoundError:
            pass
        return

    os.makedirs(state_dir, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
