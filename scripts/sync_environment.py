#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys

from environment_lib import (
    upsert_managed_block,
    write_whole_file,
    query_reg_value,
    set_reg_value,
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

powershell_profile_block = """
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$PSDefaultParameterValues['Get-Content:Encoding'] = 'UTF8'
$PSDefaultParameterValues['Select-String:Encoding'] = 'UTF8'
if ($Host.Name -eq 'ConsoleHost') {
  chcp 65001 > $null
}
"""


def main():
    state = read_state()

    print("--- PowerShell ---")
    sync_power_shell(state)

    print("--- Global gitignore ---")
    sync_global_gitignore(state)

    print("--- cmd autorun ---")
    sync_cmd_autorun(state)

    write_state(state)
    print("Environment sync complete.")


def sync_power_shell(state):
    if sys.platform != "win32":
        print("Skipping PowerShell setup because this is not Windows.")
        return

    pwsh = find_power_shell7_command()
    if not pwsh:
        pwsh = install_power_shell7(state)

    if pwsh:
        version = subprocess.run(
            [pwsh, "--version"], stdout=subprocess.PIPE, encoding="utf-8"
        ).stdout.strip()
        print(f"PowerShell 7 available: {version}")
    else:
        sys.stderr.write(
            "PowerShell 7 is unavailable. UTF-8 profile setup will still be applied "
            "to Windows PowerShell.\n"
        )

    for profile in dict.fromkeys(get_power_shell_profiles(pwsh)):
        upsert_managed_block(
            profile,
            {
                "start": "# >>> ai-workflow powershell utf8 >>>",
                "end": "# <<< ai-workflow powershell utf8 <<<",
                "body": powershell_profile_block,
                "legacyPatterns": [
                    re.compile(
                        r"# >>> ai-workflow utf8 >>>[\s\S]*?# <<< ai-workflow utf8 <<<\r?\n?"
                    ),
                    re.compile(
                        r"# >>> test-playground powershell utf8 >>>[\s\S]*?"
                        r"# <<< test-playground powershell utf8 <<<\r?\n?"
                    ),
                ],
            },
        )


def sync_global_gitignore(state):
    current_path = get_global_git_excludes_file()

    if current_path and os.path.abspath(current_path) != os.path.abspath(global_gitignore):
        sys.stderr.write(f"core.excludesFile is already set to: {current_path}\n")
        sys.stderr.write(f"Skipping registration of {global_gitignore}\n")
    elif not current_path:
        subprocess.run(
            ["git", "config", "--global", "core.excludesFile", global_gitignore],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            check=True,
        )
        state["gitCoreExcludesFileSetByAiContexts"] = True
        print(f"Registered core.excludesFile = {global_gitignore}")
    else:
        print(f"core.excludesFile already registered as {global_gitignore}")

    upsert_managed_block(
        global_gitignore,
        {
            "start": "# >>> ai-workflow global gitignore >>>",
            "end": "# <<< ai-workflow global gitignore <<<",
            "body": "plan/",
            "legacyLinePatterns": [re.compile(r"^plan/$"), re.compile(r"^backlog/$")],
        },
    )


def sync_cmd_autorun(state):
    if sys.platform != "win32":
        print("Skipping cmd autorun setup because this is not Windows.")
        return

    status = write_whole_file(cmd_autorun_file, cmd_autorun_body)
    print(
        {
            "created": f"Created {cmd_autorun_file}",
            "updated": f"Updated {cmd_autorun_file}",
            "unchanged": f"Already up to date: {cmd_autorun_file}",
        }[status]
    )

    desired = f"@{cmd_autorun_file}"
    current = query_reg_value(cmd_processor_key, "AutoRun")

    if current == desired:
        state["cmdAutorunRegSetByAiContexts"] = True
        print(f"AutoRun already registered as {desired}")
    elif not current:
        set_reg_value(cmd_processor_key, "AutoRun", desired)
        state["cmdAutorunRegSetByAiContexts"] = True
        print(f"Registered AutoRun = {desired}")
    else:
        sys.stderr.write(f"AutoRun is already set to: {current}\n")
        sys.stderr.write(f"Skipping registration of {desired}\n")


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


def install_power_shell7(state):
    if not runs("winget", ["--version"]):
        sys.stderr.write(
            "winget was not found. Install PowerShell 7 manually, then rerun sync:environment.\n"
        )
        return None

    print("Installing PowerShell 7 with winget...")
    subprocess.run(
        [
            "winget",
            "install",
            "--exact",
            "--id",
            "Microsoft.PowerShell",
            "--source",
            "winget",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        check=True,
    )
    state["powerShell7InstalledByAiContexts"] = True
    return find_power_shell7_command()


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
    if len(state) == 0:
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
