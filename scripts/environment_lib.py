# sync_environment.py / unsync_environment.py / verify_environment.py가 공유하는
# 멱등성·안전제거 메커니즘. 파일 경로·레지스트리 키를 인자로 받아 샌드박스에서도
# 같은 함수를 검증할 수 있게 한다.
import os
import re
import shutil
import subprocess
from datetime import datetime


# 마커 block을 삽입하거나 기존 block을 새 내용으로 교체한다. 반복 실행해도 block이
# 중복되지 않고 같은 상태로 수렴한다.
def upsert_managed_block(file, options):
    managed = f"{options['start']}\n{options['body'].strip()}\n{options['end']}\n"
    marker_pattern = re.compile(
        f"{escape_reg_exp(options['start'])}[\\s\\S]*?{escape_reg_exp(options['end'])}\\r?\\n?"
    )

    os.makedirs(os.path.dirname(file), exist_ok=True)

    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as handle:
            handle.write(managed)
        print(f"Created {file}")
        return

    with open(file, "r", encoding="utf-8") as handle:
        existing = handle.read()
    original = existing
    patterns = [marker_pattern, *(options.get("legacyPatterns") or [])]
    matching_pattern = next((pattern for pattern in patterns if pattern.search(existing)), None)

    if matching_pattern:
        existing = matching_pattern.sub(_literal(managed), existing, count=1)
    else:
        for line_pattern in options.get("legacyLinePatterns") or []:
            existing = "\n".join(
                line for line in re.split(r"\r?\n", existing) if not line_pattern.search(line.strip())
            )
            if existing and not existing.endswith("\n"):
                existing += "\n"
        suffix = "" if (existing.endswith("\n") or len(existing) == 0) else "\n"
        existing = f"{existing}{suffix}{managed}"

    if existing == original:
        print(f"Already up to date: {file}")
        return

    shutil.copyfile(file, f"{file}.bak-{timestamp()}")
    with open(file, "w", encoding="utf-8") as handle:
        handle.write(existing)
    print(f"Updated {file}")


# 마커 block만 제거하고 파일의 나머지(사용자 내용)는 보존한다. 제거 후 파일이
# 비면 파일 자체를 삭제한다.
def remove_managed_blocks(file, patterns):
    if not os.path.exists(file):
        print(f"Already absent: {file}")
        return

    with open(file, "r", encoding="utf-8") as handle:
        existing = handle.read()
    next_content = existing
    for pattern in patterns:
        next_content = pattern.sub("", next_content)

    if next_content == existing:
        print(f"No ai-workflow block found: {file}")
        return

    shutil.copyfile(file, f"{file}.bak-{timestamp()}")
    if len(next_content.strip()) == 0:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass
        print(f"Removed empty file: {file}")
    else:
        with open(file, "w", encoding="utf-8") as handle:
            handle.write(next_content)
        print(f"Updated {file}")


# 파일 전체를 AC 내용으로 멱등 생성/갱신한다. 'created' | 'updated' | 'unchanged' 반환.
def write_whole_file(file, body):
    os.makedirs(os.path.dirname(file), exist_ok=True)

    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as handle:
            if handle.read() == body:
                return "unchanged"
        shutil.copyfile(file, f"{file}.bak-{timestamp()}")
        with open(file, "w", encoding="utf-8") as handle:
            handle.write(body)
        return "updated"

    with open(file, "w", encoding="utf-8") as handle:
        handle.write(body)
    return "created"


# 파일 내용이 AC가 쓴 body와 동일할 때만 삭제한다(동일성 비교).
# 'removed' | 'modified' | 'absent' 반환.
def remove_if_identical(file, body):
    if not os.path.exists(file):
        return "absent"
    with open(file, "r", encoding="utf-8") as handle:
        if handle.read() != body:
            return "modified"

    shutil.copyfile(file, f"{file}.bak-{timestamp()}")
    try:
        os.remove(file)
    except FileNotFoundError:
        pass
    return "removed"


def query_reg_value(key, name):
    try:
        # 값이 없으면 reg가 stderr로 에러를 내는데, 정상적인 "없음" 케이스에서 잡음을
        # 막기 위해 stderr를 ignore한다.
        out = subprocess.run(
            ["reg", "query", key, "/v", name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            check=True,
        ).stdout
        match = re.search(f"{escape_reg_exp(name)}\\s+REG_\\w+\\s+(.+)", out)
        return match.group(1).strip() if match else ""
    except Exception:
        return ""


def set_reg_value(key, name, value):
    subprocess.run(
        ["reg", "add", key, "/v", name, "/t", "REG_SZ", "/d", value, "/f"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        check=True,
    )


def delete_reg_value(key, name):
    subprocess.run(
        ["reg", "delete", key, "/v", name, "/f"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        check=True,
    )


def runs(command, args):
    try:
        subprocess.run(
            [command, *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def timestamp():
    now = datetime.now()

    def pad(value):
        return str(value).rjust(2, "0")

    return "".join(
        [
            str(now.year),
            pad(now.month),
            pad(now.day),
            "-",
            pad(now.hour),
            pad(now.minute),
            pad(now.second),
        ]
    )


def escape_reg_exp(value):
    return re.sub(r"[.*+?^${}()|[\]\\]", lambda m: "\\" + m.group(0), value)


# re.sub replacement에서 백슬래시 등이 escape 시퀀스로 해석되는 것을 막는다.
def _literal(replacement):
    return replacement.replace("\\", "\\\\")
