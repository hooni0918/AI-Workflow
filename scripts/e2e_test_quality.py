#!/usr/bin/env python3
"""test-quality 게이트 실측 — 결제 예제(fixtures/test-quality-wallet)에 실제 변이 도구를 돌린다.

회귀 검증(verify_test_quality.py)은 가짜 도구만 쓴다. 실제 도구 출력에서만 드러나는 결함(도구 고유
상태·경로 표기 등)을 잡으려고, 기준 브랜치에 없던 결제 로직을 추가한 저장소를 만들고 테스트를
하나씩 더하며 게이트 판정이 기대와 같은지 본다. 마지막에 verify 가 통과하고, 단언을 약하게 바꾸면
오래된 결과로 처리하는지도 본다.

도구: 환경 변수 SMT 의 경로, 없으면 PATH 의 swift-mutation-testing. 설정의 tool.version 과 다른
버전이면 게이트가 미완료를 낸다. 도구가 없으면 확인 불가로 exit 2.
도구를 올릴 때 이 기대값으로 다시 실측한다. 실행에 수 분이 걸린다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "test-quality-wallet")
GATE = os.path.join(HERE, "..", "deploy", "skills", "test-quality", "scripts", "mutation_gate.py")
TOOL_VERSION = "1.5.1"
MODULE = "Packages/Wallet"

# 단계마다 더하는 테스트와, 그때 남아야 하는 미해결 변이(원래 표기 → 바뀐 표기)
STAGES = [
    ("1-happy.swift", ["&& → ||", "> → >=", ">= → >", "false → true"]),
    ("2-insufficient.swift", ["> → >=", ">= → >"]),
    ("3-boundary.swift", ["> → >="]),
    ("4-zero.swift", []),
]

CONFIG = {
    "version": 1,
    "base": "main",
    "source_extensions": [".swift"],
    "tool": {
        "name": "swift-mutation-testing",
        "version": TOOL_VERSION,
        "command": ["{smt}", "{module_path}", "--sources-path", "{sources_path}", "--no-cache",
                    "--output", "{report}"],
        "version_command": ["{smt}", "--version"],
        "timeout_seconds": 1800,
        "status_map": {"Unviable": "CompileError", "Crash": "RuntimeError"},
        "suppression_markers": ["@SwiftMutationTestingDisabled"],
        "config_files": [".swift-mutation-testing.yml"],
    },
    "modules": [{
        "name": "Wallet",
        "path": MODULE,
        "sources": [f"{MODULE}/Sources"],
        "tests": [f"{MODULE}/Tests"],
        "fingerprint": [f"{MODULE}/Package.swift"],
        "baseline": ["swift", "test", "--package-path", "{module_path}"],
    }],
}


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)


def copy(src_rel, repo, dst_rel):
    dst = os.path.join(repo, dst_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(FIXTURE, src_rel), dst)


def gate(repo, *args):
    proc = subprocess.run([sys.executable, GATE, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main():
    tool = os.environ.get("SMT") or shutil.which("swift-mutation-testing")
    if not tool or not os.path.exists(tool):
        print(f"확인 불가: swift-mutation-testing {TOOL_VERSION} 이 없습니다 (SMT 환경 변수나 PATH)")
        return 2
    failures = []
    with tempfile.TemporaryDirectory(prefix="tq-e2e-") as tmp:
        # macOS 의 /var → /private/var 같은 링크 경로는 도구가 결과 키 앞을 자른다(실측). 실제 경로를 쓴다
        repo = os.path.realpath(tmp)
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.email", "e2e@example.com")
        git(repo, "config", "user.name", "e2e")
        copy("Package.swift", repo, f"{MODULE}/Package.swift")
        copy("base/Wallet.swift", repo, f"{MODULE}/Sources/Wallet/Wallet.swift")
        copy("Tests/WalletTests/InitTests.swift", repo, f"{MODULE}/Tests/WalletTests/InitTests.swift")
        os.makedirs(os.path.join(repo, ".test-quality"))
        with open(os.path.join(repo, ".test-quality", "config.json"), "w", encoding="utf-8") as handle:
            json.dump(CONFIG, handle, indent=2)
        with open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as handle:
            handle.write(".build/\n.swiftpm/\n.test-quality/result.json\n")
        git(repo, "add", "--", "Packages", ".test-quality/config.json", ".gitignore")
        git(repo, "commit", "-q", "-m", "base")
        git(repo, "checkout", "-q", "-b", "feature")
        copy("Sources/Wallet/Wallet.swift", repo, f"{MODULE}/Sources/Wallet/Wallet.swift")

        config = os.path.join(repo, ".test-quality", "config.json")
        result_path = os.path.join(repo, ".test-quality", "result.json")
        for stage, expected in STAGES:
            copy(f"stages/{stage}", repo, f"{MODULE}/Tests/WalletTests/{stage}")
            git(repo, "add", "--", "Packages")
            git(repo, "commit", "-q", "-m", stage)
            code, output = gate(repo, "run", "--config", config, "--repo", repo, "--out", result_path,
                                "--var", f"smt={tool}", "--work-dir", os.path.join(tmp, "work", stage))
            with open(result_path, encoding="utf-8") as handle:
                result = json.load(handle)
            got = sorted(f"{m['original']} → {m['replacement']}" for m in result["unresolved"])
            want_code = 0 if not expected else 1
            ok = code == want_code and got == sorted(expected)
            print(f"{'OK ' if ok else 'FAIL'} {stage}: exit {code}, 미해결 {got}")
            if not ok:
                failures.append(stage)
                print(output)

        code, output = gate(repo, "verify", "--config", config, "--repo", repo, "--result", result_path)
        print(f"{'OK ' if code == 0 else 'FAIL'} verify: exit {code}")
        if code != 0:
            failures.append("verify")
            print(output)
        weakened = os.path.join(repo, MODULE, "Tests", "WalletTests", "3-boundary.swift")
        with open(weakened, encoding="utf-8") as handle:
            text = handle.read()
        with open(weakened, "w", encoding="utf-8") as handle:
            handle.write(text.replace("wallet.balance == 0", "wallet.balance >= 0"))
        code, output = gate(repo, "verify", "--config", config, "--repo", repo, "--result", result_path)
        print(f"{'OK ' if code == 2 else 'FAIL'} 단언을 약하게 바꾼 뒤 verify: exit {code} (오래된 결과)")
        if code != 2:
            failures.append("verify-stale")
            print(output)
    if failures:
        print(f"실측 실패: {', '.join(failures)}")
        return 1
    print("실측 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
