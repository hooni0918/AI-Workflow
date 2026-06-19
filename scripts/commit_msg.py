#!/usr/bin/env python3
# git commit-msg 훅: Conventional Commits 규칙을 Python으로 검사한다.
#
# 적용 규칙:
#   - type-enum:           conventional 표준 타입만 허용
#   - type-empty:          type 비어 있으면 금지
#   - subject-empty:       subject 비어 있으면 금지
#   - scope-enum:          [skills, contexts, rules, settings, scripts, docs] 중 하나
#   - scope-empty:         scope 비어 있으면 금지 (반드시 있어야 함)
#   - subject-case:        비활성(검사 안 함)
#   - subject-korean:      subject에 한글(가-힣 등) 포함 필수
#   - body-max-line-length: body의 각 줄 길이 200 이하
#
# git이 commit-msg 훅에 메시지 파일 경로를 argv[1]로 넘긴다. 위반 시 stderr로 사유를
# 출력하고 종료코드 1로 커밋을 거부한다(통과 시 0).
import re
import sys

# conventional commit 헤더: type(scope)!: subject
#   - scope는 선택(괄호 포함), '!'는 breaking change 표시(선택)
HEADER_PATTERN = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?: (.+)$")

# Conventional Commits 표준 type-enum.
TYPE_ENUM = [
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
]

# 이 레포에 맞춘 scope-enum.
SCOPE_ENUM = ["skills", "contexts", "rules", "settings", "scripts", "docs"]

BODY_MAX_LINE_LENGTH = 200

KOREAN_PATTERN = re.compile(r"[가-힯]")


def read_message(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


# 주석(#) 줄과 verbose diff(scissors 이후)를 메시지에서 제거한다.
def strip_comments(raw):
    lines = raw.split("\n")
    kept = []
    for line in lines:
        # `# ------------------------ >8 ------------------------` 이후는 verbose diff.
        if line.startswith("# ------------------------ >8"):
            break
        if line.startswith("#"):
            continue
        kept.append(line)
    return "\n".join(kept)


# 메시지를 header / body / footer 블록으로 나눈다(빈 줄 기준, conventional 파서 근사).
def parse(message):
    # 선행 빈 줄 제거.
    text = message.lstrip("\n")
    # 끝쪽 공백 정리(트레일링 개행은 의미 없음).
    text = text.rstrip("\n")

    lines = text.split("\n")
    header = lines[0] if lines else ""

    body_lines = []
    # header 다음, 첫 빈 줄 이후가 body. conventional 규칙은 header와 body를 빈 줄로 구분한다.
    if len(lines) > 1:
        rest = lines[1:]
        # 선행 빈 줄(구분자) 제거 후 나머지를 body로 본다.
        idx = 0
        while idx < len(rest) and rest[idx].strip() == "":
            idx += 1
        body_lines = rest[idx:]

    return {"header": header, "body_lines": body_lines}


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("commit-msg 훅: 메시지 파일 경로가 필요합니다\n")
        sys.exit(1)

    raw = read_message(sys.argv[1])
    message = strip_comments(raw)
    parsed = parse(message)
    header = parsed["header"]

    errors = []

    match = HEADER_PATTERN.match(header)
    if not match:
        # 헤더가 conventional 형식이 아니면 type/subject 규칙을 평가할 수 없다.
        errors.append(
            "헤더가 conventional 형식이 아닙니다: 'type(scope): subject' 형태여야 합니다"
        )
        type_ = None
        scope = None
        subject = None
    else:
        type_ = match.group(1)
        scope = match.group(2)  # None이면 scope 없음
        subject = match.group(4)

    # type-empty / type-enum
    if match:
        if not type_:
            errors.append("type을 비울 수 없습니다")
        elif type_ not in TYPE_ENUM:
            errors.append(f"type은 [{', '.join(TYPE_ENUM)}] 중 하나여야 합니다")

    # scope-empty [2, 'never'] → scope가 반드시 있어야 한다
    if match:
        if scope is None or scope == "":
            errors.append("scope를 비울 수 없습니다")
        elif scope not in SCOPE_ENUM:
            # scope-enum [2, 'always', [...]]
            errors.append(f"scope는 [{', '.join(SCOPE_ENUM)}] 중 하나여야 합니다")

    # subject-empty
    if match:
        if subject is None or subject.strip() == "":
            errors.append("subject를 비울 수 없습니다")
        else:
            # subject-korean [2, 'always']
            if not KOREAN_PATTERN.search(subject):
                errors.append("커밋 메시지(subject)에 한글이 포함되어야 합니다")
            # subject-case [0] → 비활성(검사하지 않음)

    # body-max-line-length [2, 'always', 200]
    for line in parsed["body_lines"]:
        if len(line) > BODY_MAX_LINE_LENGTH:
            errors.append(f"body 줄 길이가 {BODY_MAX_LINE_LENGTH}자를 초과합니다")
            break

    if errors:
        sys.stderr.write("커밋 메시지 검증 실패:\n")
        for error in errors:
            sys.stderr.write(f"  - {error}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
