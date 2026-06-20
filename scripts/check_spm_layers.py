#!/usr/bin/env python3
# SPM 로컬 패키지의 레이어 의존을 정적 검사한다.
#
# 각 Packages/<M>/Package.swift의 `.target(... dependencies: [...])` 배열을 추출해
# 레이어 규칙(허용 의존 방향)과 대조한다. 역방향·수평·미허용·사이클이면 종료코드 1로 차단한다.
#
# 왜: "빌드 성공"은 "선언된 의존 안에서 타입이 맞는다"만 보증한다. dependencies에 역방향을
# 적으면 컴파일은 통과하므로, 빌드는 레이어 단방향 규칙을 강제하지 못한다. 이 검사기는 그
# 간극을 결정론적으로(LLM·사람 판단 없이) 메우는 게이트다 — CI·pre-commit·hook 어디서나 동일.
#
# 사용:
#   python3 check_spm_layers.py <packages_dir> --rules <rules.json>
# rules.json: {"Feature": ["Domain","DesignSystem"], "Data": ["Domain","Networking"], ...}
#   키 = 모듈, 값 = 그 모듈이 의존해도 되는 하위 모듈 목록.
#   (App은 보통 컴포지션 루트라 Packages/ 밖이며 검사 대상에서 자연 제외된다.)
import json
import os
import re
import sys

# `.target(name: "X", dependencies: [ ... ])` — testTarget은 `.target(`로 시작하지 않아 제외된다.
TARGET_RE = re.compile(r'\.target\(\s*name:\s*"([^"]+)"\s*,\s*dependencies:\s*\[([^\]]*)\]', re.S)
DEP_STR_RE = re.compile(r'"([^"]+)"')


def parse_edges(packages_dir):
    # module -> set(deps). 각 패키지의 비-test 타겟 dependencies(로컬 모듈명 문자열)를 모은다.
    edges = {}
    for entry in sorted(os.listdir(packages_dir)):
        manifest = os.path.join(packages_dir, entry, "Package.swift")
        if not os.path.isfile(manifest):
            continue
        text = open(manifest, encoding="utf-8").read()
        for name, body in TARGET_RE.findall(text):
            edges.setdefault(name, set()).update(DEP_STR_RE.findall(body))
    return edges


def find_cycles(edges):
    # DFS 백엣지 검출. 자기 자신으로 돌아오는 경로를 찾는다.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {}
    cycles = []

    def dfs(u, stack):
        color[u] = GRAY
        stack.append(u)
        for v in sorted(edges.get(u, ())):
            c = color.get(v, WHITE)
            if c == GRAY and v in stack:
                cycles.append(stack[stack.index(v):] + [v])
            elif c == WHITE:
                dfs(v, stack)
        stack.pop()
        color[u] = BLACK

    for n in sorted(edges):
        if color.get(n, WHITE) == WHITE:
            dfs(n, [])
    return cycles


def main():
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    rules_path = None
    if "--rules" in sys.argv:
        idx = sys.argv.index("--rules")
        if idx + 1 < len(sys.argv):
            rules_path = sys.argv[idx + 1]

    packages_dir = positional[0] if positional else "Packages"
    if not rules_path:
        sys.stderr.write("사용법: check_spm_layers.py <packages_dir> --rules <rules.json>\n")
        sys.exit(2)
    if not os.path.isdir(packages_dir):
        sys.stderr.write(f"패키지 디렉토리 없음: {packages_dir}\n")
        sys.exit(2)

    rules = json.load(open(rules_path, encoding="utf-8"))
    known = set(rules.keys())
    edges = parse_edges(packages_dir)

    print(f"검사: {packages_dir}  (규칙: {rules_path})")
    edge_count = sum(len(v) for v in edges.values())
    print(f"모듈 {len(edges)}개, 의존 edge {edge_count}개")
    for mod in sorted(edges):
        deps = ", ".join(sorted(edges[mod])) or "(없음)"
        print(f"  {mod} → {deps}")

    violations = []
    for mod in sorted(edges):
        allowed = set(rules.get(mod, []))
        for dep in sorted(edges[mod]):
            if dep not in known:
                continue  # 외부/비레이어 의존은 검사 대상 아님
            if dep == mod:
                violations.append((mod, dep, "자기 의존"))
            elif dep not in allowed:
                kind = "역방향" if mod in set(rules.get(dep, [])) else "수평/미허용"
                violations.append((mod, dep, kind))

    cycles = find_cycles(edges)

    if violations or cycles:
        print("\n위반:")
        for m, d, k in violations:
            print(f"  FAIL  {m} → {d}  ({k})")
        for c in cycles:
            print(f"  FAIL  사이클: {' → '.join(c)}")
        sys.stderr.write(f"\n레이어 규칙 위반 {len(violations) + len(cycles)}건 — 쓰기 차단(exit 1)\n")
        sys.exit(1)

    print("\n레이어 규칙 준수: 위반 0건")


if __name__ == "__main__":
    main()
