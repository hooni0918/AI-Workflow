#!/usr/bin/env python3
"""Rule-ablation behavior bench (claude -p, isolated environment).

Why this harness exists and why it drives the CLI instead of the API:

Rule ablation measures *whether a behavior rule changes the response*. The rules
under test live in `~/.claude/rules/*.md`, which every normal `claude -p` call
and every subagent auto-loads — so a true ZERO (rule-absent) baseline is
impossible by default (the run already knows the rule). See scw
specialized/rule-ablation-bench.md lines 31-61.

Isolation mechanism (empirically verified before use):
- `--setting-sources ""` strips ALL deployed setting/memory sources (user +
  project rules, CLAUDE.md). A probe asking "do you have the one-at-a-time rule?"
  returns NO under this flag and YES without it.
- `--append-system-prompt "<base + variant target>"` injects a fully controlled
  system prompt back in. Re-probing returns YES for V1, NO for ZERO.
- Each call runs in a throwaway empty cwd so no project CLAUDE.md is in scope,
  and with no tools (advice prompts, empty dir) so responses stay pure text.

This uses the CLI's existing OAuth login — no ANTHROPIC_API_KEY required.

Eval-set JSON schema (unchanged across API/CLI harness):
{
  "rule_id": "...",
  "base_system": "...{TARGET}...",          # {TARGET} replaced per variant
  "variants": {"ZERO": "", "V1": "...", ...},
  "scenarios": [
    {"id": "P1", "type": "positive", "user": "...", "pass_when": ["ONE_AT_A_TIME"]},
    ...
  ],
  "inheritance_signatures": ["...", ...]      # if a ZERO response reuses these,
                                              # flag possible env inheritance
}

Each (scenario, variant, rep): generate with the variant system prompt, grade
into {ONE_AT_A_TIME, DUMP_ALL, ASK_CLARIFY, SINGLE}. Pass iff class in pass_when.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


CLAUDE = shutil.which("claude") or "claude"

GRADER_SYSTEM = (
    "너는 어시스턴트 응답의 *제시 형태*를 분류하는 채점자다. 내용 정확성이 아니라 형태만 본다.\n"
    "다음 4개 중 정확히 하나로 분류한다:\n"
    "- ONE_AT_A_TIME: 여러 독립 항목/제안/보기 중 하나만 제시하고 나머지는 미루며, 사용자 반응을 받은 뒤 이어가겠다고 명시적으로 멈춘다.\n"
    "- DUMP_ALL: 여러 항목/제안/보기/단계를 이 한 응답에 함께 나열한다.\n"
    "- ASK_CLARIFY: 항목을 제시하지 않고 주로 추가 정보·맥락을 되묻는다.\n"
    "- SINGLE: 과제 자체가 항목이 하나뿐이라 그 하나만 다룬다(쪼갤 다수성이 없음).\n"
    '반드시 아래 JSON만 출력한다(다른 텍스트 금지):\n'
    '{"class": "ONE_AT_A_TIME|DUMP_ALL|ASK_CLARIFY|SINGLE", "reason": "한 문장"}'
)

GRADER_USER_TMPL = "[사용자 요청]\n{user}\n\n[어시스턴트 응답]\n{response}\n\n위 응답의 제시 형태를 한 가지로 분류해라."

VALID = {"ONE_AT_A_TIME", "DUMP_ALL", "ASK_CLARIFY", "SINGLE"}


def claude_p(prompt, system, model, timeout, tries=3):
    """One isolated claude -p call. Returns stdout text, or raises on repeated failure."""
    last = ""
    for i in range(tries):
        with tempfile.TemporaryDirectory(prefix="abl_") as cwd:
            try:
                proc = subprocess.run(
                    [CLAUDE, "-p", prompt, "--model", model,
                     "--setting-sources", "", "--append-system-prompt", system],
                    cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                last = "timeout"
                time.sleep(2 * (i + 1))
                continue
        out = (proc.stdout or "").strip()
        if proc.returncode == 0 and out:
            return out
        last = f"rc={proc.returncode} err={(proc.stderr or '')[:160]}"
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"claude -p failed: {last}")


def grade(user, response, model, timeout):
    raw = claude_p(GRADER_USER_TMPL.format(user=user, response=response),
                   GRADER_SYSTEM, model, timeout)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {"class": "PARSE_ERROR", "reason": raw[:200]}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"class": "PARSE_ERROR", "reason": raw[:200]}
    if obj.get("class") not in VALID:
        return {"class": "PARSE_ERROR", "reason": str(obj)[:200]}
    return obj


def run_one(gen_model, grader_model, base_system, target, scenario, timeout):
    system = base_system.replace("{TARGET}", target)
    response = claude_p(scenario["user"], system, gen_model, timeout)
    g = grade(scenario["user"], response, grader_model, timeout)
    cls = g["class"]
    return {"class": cls, "passed": cls in scenario["pass_when"],
            "reason": g.get("reason", ""), "response": response}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=7)
    ap.add_argument("--model", default="claude-sonnet-4-6", help="generation model under test")
    ap.add_argument("--grader-model", default="claude-sonnet-4-6")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--variants", default=None, help="comma filter e.g. ZERO,V1")
    ap.add_argument("--scenarios", default=None, help="comma filter e.g. P1,C1")
    ap.add_argument("--dump-dir", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    spec = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    base_system = spec["base_system"]
    variants = spec["variants"]
    scenarios = spec["scenarios"]
    signatures = spec.get("inheritance_signatures", [])

    if args.variants:
        keep = set(args.variants.split(","))
        variants = {k: v for k, v in variants.items() if k in keep}
    if args.scenarios:
        keep = set(args.scenarios.split(","))
        scenarios = [s for s in scenarios if s["id"] in keep]

    jobs = [(s, vn, tg, rep)
            for s in scenarios
            for vn, tg in variants.items()
            for rep in range(args.reps)]

    if args.verbose:
        print(f"rule={spec['rule_id']} variants={list(variants)} "
              f"scenarios={[s['id'] for s in scenarios]} reps={args.reps} "
              f"-> {len(jobs)} runs x2 calls (gen={args.model})", file=sys.stderr)
    if args.dump_dir:
        Path(args.dump_dir).mkdir(parents=True, exist_ok=True)

    results = {s["id"]: {v: [] for v in variants} for s in scenarios}
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, args.model, args.grader_model, base_system, tg, s, args.timeout):
                (s["id"], vn, rep) for (s, vn, tg, rep) in jobs}
        for fut in as_completed(futs):
            sid, vn, rep = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"class": "ERROR", "passed": False, "reason": str(e)[:200], "response": ""}
            results[sid][vn].append(r)
            done += 1
            if args.dump_dir:
                Path(args.dump_dir, f"{sid}_{vn}_r{rep}.json").write_text(
                    json.dumps({"scenario": sid, "variant": vn, "rep": rep, **r},
                               ensure_ascii=False, indent=2), encoding="utf-8")
            if args.verbose:
                print(f"  [{done}/{len(jobs)}] {sid}/{vn} r{rep} {r['class']} "
                      f"{'PASS' if r['passed'] else 'fail'}", file=sys.stderr)

    table, inheritance = {}, []
    for s in scenarios:
        sid = s["id"]
        table[sid] = {"type": s["type"], "pass_when": s["pass_when"], "variants": {}}
        for vn in variants:
            runs = results[sid][vn]
            table[sid]["variants"][vn] = {
                "pass": sum(1 for r in runs if r["passed"]),
                "n": len(runs),
                "classes": dict(Counter(r["class"] for r in runs)),
            }
            if vn == "ZERO":
                for r in runs:
                    hit = [sg for sg in signatures if sg in r.get("response", "")]
                    if hit:
                        inheritance.append({"scenario": sid, "signatures": hit,
                                            "excerpt": r["response"][:160]})

    out = {"rule_id": spec["rule_id"], "model": args.model, "grader_model": args.grader_model,
           "reps": args.reps, "table": table, "inheritance_flags": inheritance}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    vns = list(variants)
    print(f"\n# ablation: {spec['rule_id']}  (model={args.model}, reps={args.reps})\n")
    print("| 시나리오 | type | " + " | ".join(vns) + " |")
    print("|" + "---|" * (len(vns) + 2))
    for s in scenarios:
        cells = [f"{table[s['id']]['variants'][v]['pass']}/{table[s['id']]['variants'][v]['n']}" for v in vns]
        print(f"| {s['id']} | {s['type']} | " + " | ".join(cells) + " |")
    print(f"\n환경상속 의심: {len(inheritance)}건" +
          ("".join(f"\n  - {f['scenario']}: {f['signatures']}" for f in inheritance) if inheritance else ""))


if __name__ == "__main__":
    main()
