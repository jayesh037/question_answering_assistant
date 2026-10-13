"""Parse the three documents and decide which version of a clause is in force on a date.

Only this module knows about document structure. Every citation the system emits goes through
cite(), which fails loudly if the (document, clause) pair does not exist in the parsed files,
so a clause number can never be invented.
"""
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "ai-2-data"
MASTER, CIRC, FAQ = "policy_master_v1", "circular_2026_08_amendment", "merchant_faq_2026-03"
MASTER_EFFECTIVE = date(2026, 1, 1)
FAQ_UPDATED = date(2026, 3, 12)

# Amendment metadata, read by hand from the circular header and item D's "(Effective ...)" line.
# (circular item, master clause it targets, action, effective date)
AMENDMENTS = [
    ("A", "1.1", "replace", date(2026, 8, 1)),
    ("B", "2.1", "replace", date(2026, 8, 1)),
    ("C", "2.3", "replace", date(2026, 8, 1)),
    ("D", "3.3", "delete", date(2026, 9, 1)),  # the only item with its own, later date
    ("E", "4.3", "replace", date(2026, 8, 1)),
]


def _read(name):
    return (DATA_DIR / f"{name}.md").read_text(encoding="utf-8")


def _parse_master(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"^[\s#>*\-]*(\d+\.\d+)[.)]?\s+(.*\S)", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("*")
    return out


def _parse_circular(text):
    out, last = {}, None
    for line in text.splitlines():
        s = line.strip().strip("*")
        m = re.match(r"^([A-F])[.)]\s+(.*\S)", s)
        if m:
            last = m.group(1)
            out[last] = m.group(2)
        elif last and s.lower().startswith("(effective"):
            out[last] += " " + s  # the effective-date line belongs to the item above it
    return out


def _parse_faq(text):
    qa, cur, n = {}, None, 0
    for raw in text.splitlines():
        line = raw.strip().strip("*#> ").strip()
        if not line or line.lower().startswith("merchant faq"):
            continue
        if line.endswith("?"):
            n += 1
            cur = f"Q{n}"
            qa[cur] = [line, ""]
        elif cur:
            qa[cur][1] = (qa[cur][1] + " " + line).strip()
    return qa


MASTER_CLAUSES = _parse_master(_read(MASTER))
CIRC_ITEMS = _parse_circular(_read(CIRC))
FAQ_QA = _parse_faq(_read(FAQ))


def _validate():
    assert len(MASTER_CLAUSES) == 17, f"expected 17 master clauses, parsed {len(MASTER_CLAUSES)}"
    assert set(CIRC_ITEMS) == set("ABCDEF"), f"circular items parsed: {sorted(CIRC_ITEMS)}"
    assert len(FAQ_QA) == 5, f"expected 5 FAQ entries, parsed {len(FAQ_QA)}"
    assert "September" in CIRC_ITEMS["D"], "item D lost its own effective date"
    for item, target, _, _ in AMENDMENTS:
        assert target in MASTER_CLAUSES and item in CIRC_ITEMS


_validate()


def clause_text(doc, ref):
    if doc == MASTER:
        return MASTER_CLAUSES.get(ref)
    if doc == CIRC:
        return CIRC_ITEMS.get(ref)
    if doc == FAQ and ref in FAQ_QA:
        return " ".join(FAQ_QA[ref])
    return None


def cite(doc, ref):
    text = clause_text(doc, ref)
    if text is None:
        raise KeyError(f"refusing to cite non-existent clause {doc}:{ref}")
    return {"document": doc, "clause": ref, "text": text}


@dataclass(frozen=True)
class Version:
    doc: str
    ref: str
    text: str
    kind: str  # original | replaced | deleted


def in_force(ref, as_of):
    """Version of master clause `ref` in force on `as_of`; None if no policy yet / no such clause."""
    if as_of < MASTER_EFFECTIVE or ref not in MASTER_CLAUSES:
        return None
    v = Version(MASTER, ref, MASTER_CLAUSES[ref], "original")
    for item, target, action, eff in sorted(AMENDMENTS, key=lambda a: a[3]):
        if target == ref and eff <= as_of:
            v = Version(CIRC, item, CIRC_ITEMS[item], "deleted" if action == "delete" else "replaced")
    return v
