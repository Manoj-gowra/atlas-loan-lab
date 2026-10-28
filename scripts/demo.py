"""See what the system produced.

    python scripts/demo.py                  # all 10 applications, summary table
    python scripts/demo.py --app APP-006    # one application: rules, explanation, investigation, packet, trace
    python scripts/demo.py --solution       # the reference solution
    ATLAS_MODE=anthropic python scripts/demo.py --app APP-001   # real Claude (needs an API key)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "solutions" if "--solution" in sys.argv else ROOT))

from atlas import config, data_access  # noqa: E402
from atlas.pipeline import process_application  # noqa: E402


def show_one(app_id: str) -> None:
    c = process_application(app_id)
    r = c.rule_report
    print(f"=== {app_id}: {c.status} | route={r.route if r else '-'} | recommendation={c.recommendation}")
    print(f"    flags={c.flags} | triggers={c.triggers} | review={c.review_fields}\n")
    for res in (r.results if r else []):
        print(f"  {res.rule_id:<17} {res.status:<10} {res.detail}  [{res.policy_ref}]")
    if c.explanation:
        print(f"\n--- Explanation (attempts {c.explanation.attempts}) ---\n{c.explanation.text}")
    if c.investigation:
        inv = c.investigation
        print(f"\n--- Investigation: {inv.status} -> {inv.recommendation} {inv.reason}")
        for f in inv.findings:
            print(f"  [{f.source_specialist}] {f.finding}")
        for f in inv.unverified_asides:
            print(f"  UNVERIFIED aside [{f.source_specialist}] {f.finding}")
        for u in inv.unable_to_check:
            print(f"  not checked: {u}")
    if c.packet:
        print(f"\n--- Approval packet: needs {c.packet['required_authority']}, triggers {c.packet['triggers']}")
    print(f"\n--- Memo ---\n{c.memo}\n\n--- Trace ---")
    for s in c.trace.spans:
        a = s.attrs
        if s.kind == "llm":
            who = f"[{a['member']}] " if a.get("member") else ""
            print(f"  {who}{s.name:<22} {a['model']:<18} cache={a['cache']:<5} in={a['input_tokens']:<5} "
                  f"out={a['output_tokens']:<4} ${a['cost_usd']:.5f} {s.latency_s:.2f}s")
        elif s.kind == "tool":
            print(f"  [{a.get('member')}] {s.name:<30} authorized={a.get('authorized')} error={a.get('is_error')}")
        elif s.kind == "retrieval":
            print(f"  retrieval {a['chunk_ids']}")
    print(f"\n  total: ${c.trace.cost_usd:.4f}, {c.trace.latency_s:.1f}s (trace: runs/traces/{app_id}.jsonl)")


def show_all() -> None:
    print(f"{'app':<8} {'route':<12} {'recommend':<10} {'triggers':<38} {'flags':<26} {'cost':>8} {'time':>6}")
    total = 0.0
    ids = data_access.list_application_ids()
    for app_id in ids:
        c = process_application(app_id)
        total += c.trace.cost_usd
        print(f"{app_id:<8} {(c.rule_report.route if c.rule_report else '-'):<12} {str(c.recommendation):<10} "
              f"{','.join(c.triggers) or '-':<38} {','.join(c.flags) or '-':<26} ${c.trace.cost_usd:>7.4f} {c.trace.latency_s:>5.1f}s")
    print(f"\nAverage cost per application: ${total / len(ids):.4f}  (mode: {config.mode()})")


if __name__ == "__main__":
    if "--app" in sys.argv:
        show_one(sys.argv[sys.argv.index("--app") + 1])
    else:
        show_all()
