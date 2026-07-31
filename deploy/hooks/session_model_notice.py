#!/usr/bin/env python3
"""ios-workflow 세션 진입 시 권장 모델을 안내하는 UserPromptSubmit hook.

세션 모델은 하네스가 프로그램으로 바꿀 수 없다(hook 은 모델 변경 불가,
settings.json 의 model 은 세션 시작 시 1회만 읽힘, 현재 모델은 SessionStart
에서만 그마저 보장 없이 전달). 그래서 차단(decision)이 아니라 안내만 한다 —
현재 모델을 읽을 수 없어 차단하면 오차단이 된다.

세션 판정(/plan/ 스캔)은 하지 않는다. 그건 mino 스킬의 단일 책임이고,
여기서 복제하면 판정 규칙이 두 곳으로 갈린다. 이 hook 은 표만 공급한다.
"""
import json
import re
import sys

# ios-workflow SKILL.md 「세션」 표 (6) 권장 모델 칸의 사본.
# 표가 바뀌면 여기도 함께 고친다 — 사유까지 옮겨 적어 사용자가 판단할 수 있게 한다.
SESSION_MODELS = {
    "BG": ("Opus", "PR 분할이 전 세션의 루트 결정 — 오판이 도미노로 전파"),
    "MARKUP": (
        "Sonnet (figma URL) / Opus (캡처-only·개인)",
        "URL 은 노드값이 정답이라 결정론적 번역, 캡처·개인은 디자인을 역추론",
    ),
    "PR_{N}_PLAN": ("Opus", "stub 시그니처가 다음 PR 의 공개 계약 — 오판 시 도미노 오염"),
    "PR_{N}_IMPL": ("Sonnet", "PLAN 이 방침을 확정한 경우. 알고리즘 판단이 남았으면 Opus"),
    "PR_{N}_WRITING": ("Opus", "구현 맥락 없이 파일만 보고 의도를 추론 — 오독 비용 큼"),
}

# /mino, /ios-workflow, /ai-workflow:ios-workflow (플러그인 네임스페이스) 모두 잡는다.
ENTRY_RE = re.compile(r"^\s*/(?:[\w.-]+:)?(mino|ios-workflow)\b", re.IGNORECASE)
# 프롬프트에 세션이 명시된 경우: /ios-workflow PR_1_PLAN 실무
SESSION_RE = re.compile(r"\b(BG|MARKUP|PR_(\d+)_(PLAN|IMPL|WRITING))\b")


def normalize(session: str) -> str:
    """PR_1_PLAN → PR_{N}_PLAN (표 키로 정규화)."""
    return re.sub(r"PR_\d+_", "PR_{N}_", session)


def build_notice(prompt_text: str) -> str | None:
    if not ENTRY_RE.match(prompt_text):
        return None

    found = SESSION_RE.search(prompt_text)
    if found:
        session = found.group(1)
        key = normalize(session)
        if key not in SESSION_MODELS:
            return None
        model, reason = SESSION_MODELS[key]
        rows = [f"- **{session}** → {model} ({reason})"]
        head = f"{session} 세션 진입입니다."
    else:
        rows = [
            f"- **{name}** → {model} ({reason})"
            for name, (model, reason) in SESSION_MODELS.items()
        ]
        head = "ios-workflow 세션 진입입니다. 판정된 세션의 권장 모델을 확인하세요."

    body = "\n".join(rows)
    return (
        f"{head}\n\n"
        f"세션별 권장 구동 모델:\n{body}\n\n"
        "현재 모델이 권장과 다르면 **작업을 시작하기 전에** 사용자에게 "
        "`/model <권장>` 전환을 요청하고 답을 기다린다. 사용자가 현재 모델로 "
        "진행하겠다고 하면 그대로 진행한다.\n"
        "서브에이전트 모델은 이 안내와 무관하다 — `agents/` 정의가 강제한다."
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # 입력이 깨져도 프롬프트를 막지 않는다

    notice = build_notice(payload.get("prompt_text") or "")
    if not notice:
        return 0

    json.dump(
        {
            "additionalContext": notice,
            "systemMessage": "ios-workflow 진입 — 권장 구동 모델을 확인하세요.",
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
