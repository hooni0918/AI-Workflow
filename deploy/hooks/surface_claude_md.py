#!/usr/bin/env python3
"""폴더 CLAUDE.md 표면화 훅.

Glob/Grep 탐색 시점에 대상 경로의 미로드 CLAUDE.md "경로만" 주입해 선읽기를 유도.
도구는 차단하지 않는다.
"""
import hashlib
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import read_payload, get_cwd, get_session_id, add_context  # noqa: E402

MARKER_PREFIX = "claude-md-surface-"
CLEANUP_SENTINEL = os.path.join(tempfile.gettempdir(), f"{MARKER_PREFIX}last-cleanup")
STALE_MS = 7 * 24 * 60 * 60 * 1000
CLEANUP_INTERVAL_MS = 24 * 60 * 60 * 1000


def _now_ms():
    return time.time() * 1000


def static_prefix(pattern):
    """Glob pattern에서 와일드카드(*?[{) 등장 전까지의 정적 디렉터리 접두."""
    segs = str(pattern).replace("\\", "/").split("/")
    out = []
    for s in segs:
        if not s or re.search(r"[*?[{]", s):
            break
        out.append(s)
    return "/".join(out)


def resolve_target(payload):
    cwd = get_cwd(payload)
    input_ = payload.get("tool_input") or {}
    path_val = input_.get("path") if isinstance(input_, dict) else None
    base = path_val if isinstance(path_val, str) and path_val else cwd
    if not os.path.isabs(base):
        base = os.path.abspath(os.path.join(cwd, base))
    # Grep의 pattern은 내용 정규식이라 경로 결합 대상이 아니다 — Glob만 결합.
    if payload.get("tool_name") == "Glob" and isinstance(input_.get("pattern"), str):
        prefix = static_prefix(input_["pattern"])
        if prefix:
            base = os.path.abspath(os.path.join(base, prefix))
    return base


def collect_claude_mds(target, cwd):
    """target부터 위로 올라가며 실재하는 CLAUDE.md를 모은다."""
    loaded = set()
    d = os.path.abspath(cwd)
    while True:
        loaded.add(os.path.join(d, "CLAUDE.md").lower())
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent

    found = []
    directory = os.path.abspath(target)
    try:
        if os.path.isfile(directory):
            directory = os.path.dirname(directory)
        elif not os.path.exists(directory):
            raise FileNotFoundError
    except Exception:
        # 존재하지 않는 깊이면 실재하는 조상까지 올라간다.
        while not os.path.exists(directory):
            parent = os.path.dirname(directory)
            if parent == directory:
                break
            directory = parent
    # JS의 statSync 예외(비존재) 경로도 동일하게 조상 상승 처리.
    if not os.path.exists(directory):
        while not os.path.exists(directory):
            parent = os.path.dirname(directory)
            if parent == directory:
                break
            directory = parent

    while True:
        md = os.path.join(directory, "CLAUDE.md")
        if os.path.exists(md) and md.lower() not in loaded:
            found.append(md)
        is_project_root = os.path.exists(os.path.join(directory, ".git"))
        parent = os.path.dirname(directory)
        if is_project_root or parent == directory:
            break
        directory = parent
    return found


def take_unseen(mds, session_id):
    """세션·경로당 1회만 주입."""
    out = []
    for md in mds:
        h = hashlib.sha1(md.lower().encode("utf-8")).hexdigest()[:16]
        marker = os.path.join(tempfile.gettempdir(), f"{MARKER_PREFIX}{session_id}-{h}")
        try:
            if os.path.exists(marker):
                continue
            with open(marker, "w", encoding="utf-8") as f:
                f.write(md)
            out.append(md)
        except Exception:
            # 마커 기록 실패 시 누락보다 중복 주입이 낫다.
            out.append(md)
    return out


def cleanup_stale_markers():
    """마커 누적 청소: 하루 1회만 tmpdir을 훑어 7일 경과 마커를 지운다."""
    try:
        now = _now_ms()
        try:
            if now - (os.stat(CLEANUP_SENTINEL).st_mtime * 1000) < CLEANUP_INTERVAL_MS:
                return
        except Exception:
            pass  # sentinel 없음 — 청소 진행
        with open(CLEANUP_SENTINEL, "w", encoding="utf-8") as f:
            f.write("")
        tmp = tempfile.gettempdir()
        for name in os.listdir(tmp):
            if not name.startswith(MARKER_PREFIX):
                continue
            p = os.path.join(tmp, name)
            try:
                if now - (os.stat(p).st_mtime * 1000) > STALE_MS:
                    os.unlink(p)
            except Exception:
                continue
    except Exception:
        # 청소 실패는 무해
        pass


def main():
    try:
        payload = read_payload()
        # codex는 PreToolUse를 '*'로 통합 등록하므로 대상 도구가 아니면 self-skip.
        if payload.get("tool_name") != "Glob" and payload.get("tool_name") != "Grep":
            sys.exit(0)
        cwd = get_cwd(payload)
        if not cwd:
            sys.exit(0)

        mds = collect_claude_mds(resolve_target(payload), cwd)
        if not mds:
            sys.exit(0)
        fresh = take_unseen(mds, get_session_id(payload) or "nosession")
        if not fresh:
            sys.exit(0)
        cleanup_stale_markers()

        add_context(
            "[폴더 규칙] 탐색 대상 경로에 적용되는 CLAUDE.md가 있다 (하위 디렉터리 CLAUDE.md는 Read 전까지 자동 로드되지 않는다):\n"
            + "\n".join(f"  {p}" for p in fresh)
            + "\n이 폴더 하위에 파일을 만들거나 배치·네이밍·구조를 결정하기 전에 위 파일을 Read로 읽는다. "
            "내용이 다른 문서를 가리키는 포인터면 그 문서를 끝까지 따라가 본문 규칙을 확인한다 — 한 줄 포인터에서 멈추지 않는다.",
            "PreToolUse",
        )
    except SystemExit:
        raise
    except Exception:
        # 표면화 실패가 탐색을 막아서는 안 된다.
        sys.exit(0)


if __name__ == "__main__":
    main()
