"""Run policy_qa on eval.json and print a score table. A question passes only if status, answer text and citations all match."""
import json, sys
from policy_qa import ask

def main(path="eval.json"):
    items = json.load(open(path, encoding="utf-8"))
    rows, passed = [], 0
    for it in items:
        r = ask(it["question"], it["as_of_date"], context=it.get("context"))
        got = {f"{c['document']}:{c['clause']}" for c in r["citations"]}
        s_ok = r["status"] == it["expected_status"]
        a_ok = all(t.lower() in r["answer"].lower() for t in it["expected_contains"])
        c_ok = set(it["expected_citations"]) <= got
        ok = s_ok and a_ok and c_ok
        passed += ok
        rows.append((it["id"], "ADV" if it["adversarial"] else "", s_ok, a_ok, c_ok, ok, r["status"]))
    print(f"{'id':<6}{'type':<5}{'status':<8}{'answer':<8}{'cites':<7}{'PASS':<6}got")
    for i, t, s, a, c, ok, st in rows:
        f = lambda b: "ok" if b else "FAIL"
        print(f"{i:<6}{t:<5}{f(s):<8}{f(a):<8}{f(c):<7}{'PASS' if ok else 'FAIL':<6}{st}")
    n_adv = sum(1 for r in rows if r[1]); p_adv = sum(1 for r in rows if r[1] and r[5])
    print(f"\nTotal {passed}/{len(rows)}  |  adversarial {p_adv}/{n_adv}")
    return 0 if passed == len(rows) else 1

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
