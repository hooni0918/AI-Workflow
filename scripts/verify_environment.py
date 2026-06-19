#!/usr/bin/env python3
# environment_lib.py의 멱등성·안전제거 계약을 샌드박스에서 검증한다.
# 실제 사용자 환경(실프로필·실레지스트리·winget)은 건드리지 않는다.
# 파일 메커니즘은 임시 디렉토리에서, 레지스트리는 버리는 테스트 키에서만 돌린다.
# exit 0: 모든 계약 통과, exit 1: 위반.
import os
import re
import shutil
import subprocess
import sys
import tempfile

from environment_lib import (
    upsert_managed_block,
    remove_managed_blocks,
    write_whole_file,
    remove_if_identical,
    query_reg_value,
    set_reg_value,
    delete_reg_value,
    escape_reg_exp,
)

failures = []


def check(name, condition):
    if condition:
        print(f"  OK   {name}")
    else:
        sys.stderr.write(f"  FAIL {name}\n")
        failures.append(name)


def block_pattern(start, end):
    return re.compile(f"{escape_reg_exp(start)}[\\s\\S]*?{escape_reg_exp(end)}\\r?\\n?")


def verify_file_mechanisms(sandbox):
    print("--- whole-file 멱등 ---")
    whole = os.path.join(sandbox, "whole.txt")
    check("최초 write는 'created'", write_whole_file(whole, "A\n") == "created")
    check("같은 내용 재write는 'unchanged'", write_whole_file(whole, "A\n") == "unchanged")
    check("다른 내용 write는 'updated'", write_whole_file(whole, "B\n") == "updated")

    print("--- 동일성 기반 제거 ---")
    ident = os.path.join(sandbox, "ident.txt")
    write_whole_file(ident, "OWNED\n")
    with open(ident, "w", encoding="utf-8") as handle:
        handle.write("USER EDITED\n")
    check(
        "수정된 파일은 'modified'로 보존",
        remove_if_identical(ident, "OWNED\n") == "modified" and os.path.exists(ident),
    )
    with open(ident, "w", encoding="utf-8") as handle:
        handle.write("OWNED\n")
    check(
        "원본 일치 시 'removed'",
        remove_if_identical(ident, "OWNED\n") == "removed" and not os.path.exists(ident),
    )
    check(
        "없는 파일은 'absent'",
        remove_if_identical(os.path.join(sandbox, "nope.txt"), "OWNED\n") == "absent",
    )

    print("--- managed-block 멱등 + 선택 제거 ---")
    start = "# >>> verify test >>>"
    end = "# <<< verify test <<<"
    managed = os.path.join(sandbox, "managed.txt")
    with open(managed, "w", encoding="utf-8") as handle:
        handle.write("USER LINE\n")
    upsert_managed_block(managed, {"start": start, "end": end, "body": "managed body"})
    upsert_managed_block(managed, {"start": start, "end": end, "body": "managed body"})
    with open(managed, "r", encoding="utf-8") as handle:
        after_upsert = handle.read()
    check("2회 upsert 후 block 1개만 존재", len(after_upsert.split(start)) - 1 == 1)
    check("upsert가 사용자 줄 보존", "USER LINE" in after_upsert)
    check("upsert가 block body 포함", "managed body" in after_upsert)

    remove_managed_blocks(managed, [block_pattern(start, end)])
    with open(managed, "r", encoding="utf-8") as handle:
        after_remove = handle.read()
    check("removeManagedBlocks가 block 제거", "managed body" not in after_remove)
    check("removeManagedBlocks가 사용자 줄 보존", "USER LINE" in after_remove)


def verify_registry_mechanisms():
    if sys.platform != "win32":
        print("--- 레지스트리: Windows 아님, skip ---")
        return

    print("--- 레지스트리 set/query/delete 왕복 ---")
    test_key = "HKCU\\Software\\ai-workflow-verify"
    try:
        set_reg_value(test_key, "AutoRun", "@C:\\verify\\test.cmd")
        check("set 후 query가 같은 값 반환", query_reg_value(test_key, "AutoRun") == "@C:\\verify\\test.cmd")
        delete_reg_value(test_key, "AutoRun")
        check("delete 후 query가 빈 값", query_reg_value(test_key, "AutoRun") == "")
        check("없는 키 query는 빈 값", query_reg_value(test_key, "Missing") == "")
    finally:
        subprocess.run(
            ["reg", "delete", test_key, "/f"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )


def main():
    sandbox = tempfile.mkdtemp(prefix="ac-verify-env-")
    try:
        verify_file_mechanisms(sandbox)
        verify_registry_mechanisms()
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    if len(failures) > 0:
        sys.stderr.write(f"\n검증 실패 {len(failures)}건: {', '.join(failures)}\n")
        sys.exit(1)
    print("\nenvironment 메커니즘 계약 정상")


if __name__ == "__main__":
    main()
