"""All arithmetic and calendar logic. No language model, no floats: Decimal only."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from .docs import CIRC, MASTER

GST_RATE = Decimal("0.18")
GST_CITE = (MASTER, "2.4")

# name -> [(effective_from, value, citations)], later entries supersede earlier ones.
PARAMS = {
    "rate_small": [
        (date(2026, 1, 1), Decimal("0.003"), [(MASTER, "2.1")]),
        (date(2026, 8, 1), Decimal("0.0025"), [(CIRC, "B")]),
    ],
    "rate_large": [(date(2026, 1, 1), Decimal("0.005"), [(MASTER, "2.2")])],
    "cap_small": [
        (date(2026, 1, 1), Decimal(15), [(MASTER, "2.3")]),
        (date(2026, 8, 1), Decimal(15), [(CIRC, "C")]),
    ],
    "cap_large": [
        (date(2026, 1, 1), Decimal(15), [(MASTER, "2.2"), (MASTER, "2.3")]),
        (date(2026, 8, 1), Decimal(25), [(CIRC, "C")]),
    ],
}


def param(name, as_of):
    cur = None
    for eff, val, cites in PARAMS[name]:
        if eff <= as_of:
            cur = (val, cites)
    return cur


def q2(x):
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def mdr_for(amount, size, as_of):
    rate, rc = param(f"rate_{size}", as_of)
    cap, cc = param(f"cap_{size}", as_of)
    raw = q2(Decimal(amount) * rate)
    mdr = min(raw, cap)  # the cap applies to MDR only; GST is added afterwards (clause 2.4)
    gst = q2(mdr * GST_RATE)
    return {"size": size, "amount": Decimal(amount), "rate": rate, "raw_mdr": raw, "cap": cap,
            "capped": raw > cap, "mdr": mdr, "gst": gst, "total": mdr + gst, "cites": rc + cc + [GST_CITE]}


def is_working_day(d, holidays=()):
    return d.weekday() != 6 and d not in set(holidays)  # Sundays excluded; holidays supplied by caller


def nth_working_day_after(start, n, holidays=()):
    d, count = start, 0
    while count < n:
        d += timedelta(days=1)
        if is_working_day(d, holidays):
            count += 1
    return d


def inr(x):
    x = Decimal(x)
    whole, frac = f"{x:.2f}".split(".")
    if len(whole) > 3:
        head, tail, parts = whole[:-3], whole[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return "₹" + whole + ("" if frac == "00" else "." + frac)


def fmt_date(d):
    return f"{d.day} {d.strftime('%b %Y')}"
