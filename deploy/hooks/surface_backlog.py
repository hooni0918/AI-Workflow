#!/usr/bin/env python3
"""백로그 표면화 훅.

cwd 프로젝트와 연결된 백로그 폴더가 있으면 세션·폴더당 1회 컨텍스트 주입.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import read_payload, get_cwd, get_session_id, add_context  # noqa: E402

# 백로그는 master가 아니라 ai-workflow-backlog 워크트리(backlog 브랜치)에 있다.
# 워크트리가 없는 기기에서는 조용히 no-op 한다.
BACKLOG_ROOT = os.path.join(
    os.path.expanduser("~"),
    "WebstormProjects",
    "main",
    "ai-workflow-backlog",
    "backlog",
)

# 세션당 폴더당 "전체 블록"은 1회만 주입하기 위한 상태 저장 위치.
STATE_DIR = os.path.join(tempfile.gettempdir(), "claude-backlog-surfaced")


def project_from_cwd(cwd):
    """cwd: .../WebstormProjects/<group>/<project>/... → <project>"""
    segs = [s for s in str(cwd).replace("\\", "/").split("/") if s]
    i = -1
    for idx, s in enumerate(segs):
        if s.lower() == "webstormprojects":
            i = idx
            break
    if i >= 0 and len(segs) > i + 2:
        return segs[i + 2]
    return ""


def has_markdown(directory):
    stack = [directory]
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except Exception:
            continue
        for e in entries:
            if e.is_dir():
                stack.append(os.path.join(d, e.name))
            elif e.is_file() and e.name.endswith(".md"):
                return True
    return False


def seen_file(session_id):
    return os.path.join(STATE_DIR, f"{session_id}.json")


def already_surfaced(session_id, key):
    try:
        with open(seen_file(session_id), "r", encoding="utf-8") as f:
            seen = json.load(f)
        return isinstance(seen, list) and key in seen
    except Exception:
        return False


def mark_surfaced(session_id, key):
    seen = []
    try:
        with open(seen_file(session_id), "r", encoding="utf-8") as f:
            prev = json.load(f)
        if isinstance(prev, list):
            seen = prev
    except Exception:
        pass  # 첫 안내
    if key not in seen:
        seen.append(key)
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(seen_file(session_id), "w", encoding="utf-8") as f:
        f.write(json.dumps(seen))


def main():
    try:
        payload = read_payload()
        project = project_from_cwd(get_cwd(payload))
        if not project:
            sys.exit(0)

        # cwd 프로젝트 → 백로그 폴더. AC 본체는 this/, 그 외는 projects/<project>/.
        rel = "this" if project == "ai-workflow" else os.path.join("projects", project)
        folder = os.path.join(BACKLOG_ROOT, rel)
        if not os.path.exists(folder) or not has_markdown(folder):
            sys.exit(0)

        # 전체 블록은 세션당 폴더당 1회만 주입. session_id가 없으면(폴백) 매 턴 전체 블록.
        session_id = get_session_id(payload)
        rel_posix = rel.replace(os.sep, "/")
        if session_id:
            if already_surfaced(session_id, rel_posix):
                sys.exit(0)
            mark_surfaced(session_id, rel_posix)

        add_context(
            f"[백로그 표면화] 현재 작업 디렉터리({project})에 연결된 백로그 폴더가 있다:\n"
            f"  {folder}\n"
            "이 폴더에는 미해결 작업뽐 아니라 학습·정리 대기 노트도 들어 있다. "
            "이 세션에서 아직 이 폴더를 보지 않았다면 지금 한 번 훑어(Glob) 항목 제목을 확인한다 — 관련성은 폴더를 본 뒤에 판단하고, 보기 전에 \"무관\"으로 단정하지 않는다. "
            "파일명이 작업 주제를 분명히 드러내지 않으면 파일명만으로 관련·무관을 단정하지 말고, 그 파일을 열어 내용으로 판단한다. "
            "열어본 뒤 각도가 조금 다르다는 이유로 \"무관\"이라 스스로 단정해 무시하지 않는다 — 같은 영역·대상·메커니즘을 건드리면 구체적 각도가 달라도 부분 관련으로 보고 표면화한다. 부분 관련 항목을 최종적으로 끌어들일지 말지는 사용자가 정하며, 에이전트가 조용히 무관 처리할 권한이 아니다. "
            "상위 폴더명이 무관해 보여도 그 폴더 하위 파일명이 현재 작업과 겹치면(예: /recruitment 작업 중 \"면접\"이 박힌 파일), 폴더명으로 덮어 무관 단정하지 말고 그 파일을 열다. 폴더명은 하위 파일의 관련 신호를 가리지 못한다. "
            "directed 슬래시 커맨드를 처리하는 중이라도 이 확인을 먼저 끼워 넣는다. 이미 목록을 봤다면 다시 훑지 말고 기억한 목록으로 판단한다. "
            "현재 작업과 겹치는 항목이 있으면 \"이 백로그도 같이 다룰까요?\"로 사용자에게 제안하고 허락을 받은 뒤에만 작업에 포함한다. "
            "내용 판단을 위해 파일을 열어보는 것은 괜찮지만, 허락 없이 백로그 항목을 현재 작업 범위에 끌어들이거나 산출물·스펙에 반영하지 않는다 — 읽고 곲장 흡수하지 말고 반드시 먼저 제안·확인한다. "
            "백로그 파일을 작업 이해용 참고로 읽었더라도, 그 안에 지금 손대려는 대상·메커니즘을 건드리는 미해결 항목이 있으면 그 항목을 별도로 호명해 \"이 백로그도 같이 다룰까요?\"로 제안한다. 읽어서 맥락에 흡수했다는 이유로 제안 의무가 사라지지 않는다 — 자기 진단·수정안으로 곲장 넘어가기 전에 그 항목을 명시적으로 띄운다. "
            "백로그가 현재 슬래시 커맨드나 작업의 직접 입력물·대상처럼 보여도 예외가 아니다 — 관련성을 인지하면 곲장 진행하지 말고 멈춰서 \"이 백로그를 이번 작업에 반영할까요?\"로 제안한 뒤 허락을 기다린다. 관련성만 보고하고 진행하거나, 흡수 범위·기본값을 스스로 정해 밀고 나가지 않는다. "
            "겹치는 게 없으면 조용히 넘어간다."
        )
    except SystemExit:
        raise
    except Exception:
        # 표면화 실패가 프롬프트 처리를 막아서는 안 된다.
        sys.exit(0)


if __name__ == "__main__":
    main()
