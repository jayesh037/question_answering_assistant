"""ask(question, as_of_date) -> answer, citations, status.

Offline, rule-based. Each handler recognises one kind of question by keywords, resolves which clause
versions are in force on as_of_date, takes numbers from calc.py, and cites only real clauses.
Anything no handler recognises is CANNOT_ANSWER rather than a guess.
"""
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from . import calc, docs
from .calc import fmt_date, inr
from .docs import CIRC, FAQ, MASTER

ANSWERED, RESOLVED, CANNOT = "ANSWERED", "CONFLICT_RESOLVED", "CANNOT_ANSWER"
EFF_AUG, EFF_SEP, CIRC_ISSUED = date(2026, 8, 1), date(2026, 9, 1), date(2026, 7, 20)
PER_TXN, ENHANCED = Decimal(100000), Decimal(200000)

AMT = re.compile(r"(?:rs\.?|₹|inr)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?", re.I)


def _resp(answer, status, cites, how=None, calc_=None):
    seen = []
    for c in cites:
        if c not in seen:
            seen.append(c)
    return {"answer": answer, "status": status, "resolution": how,
            "citations": [docs.cite(d, r) for d, r in seen], "calculation": calc_}


def amounts(q):
    """Transaction amounts in the text; thresholds like 'above Rs.10 lakh monthly' are skipped."""
    out = []
    for m in AMT.finditer(q):
        pre, post = q[max(0, m.start() - 14):m.start()], q[m.end():m.end() + 14]
        if re.search(r"(above|over|below|under|exceed\w*|than|up to)\s*$", pre) or re.search(r"monthly|volume", post):
            continue
        v = Decimal(m.group(1).replace(",", "").rstrip(".") or 0)
        v *= {"lakh": 100000, "lac": 100000, "crore": 10000000}.get((m.group(2) or "").lower(), 1)
        out.append(v)
    return out


def _size(ctx):
    if re.search(r"\blarge\b|(above|over|more than|exceeding)\s*(rs\.?|₹)?\s*10 lakh", ctx):
        return "large"
    if re.search(r"\bsmall\b|(up to|below|under)\s*(rs\.?|₹)?\s*10 lakh", ctx):
        return "small"
    return None


# ---------------------------------------------------------------- handlers

def h_clause(q, ctx, as_of, hol):
    m = re.search(r"clause\s+(\d+\.\d+)", q)
    if not m:
        return None
    ref = m.group(1)
    v = docs.in_force(ref, as_of)
    if v is None:
        return _resp(f"The Master Document has no clause {ref}, so I cannot say anything about it.", CANNOT, [])
    if v.kind == "deleted":
        return _resp(f"No. Clause {ref} is not in force on {fmt_date(as_of)}: circular item {v.ref} deleted it "
                     f"with effect from 1 Sep 2026. Its old text was: \"{docs.MASTER_CLAUSES[ref]}\"", RESOLVED,
                     [(CIRC, v.ref), (MASTER, ref)],
                     "Later circular supersedes the Master Document once its effective date has passed.")
    if v.kind == "replaced":
        return _resp(f"Clause {ref} as in force on {fmt_date(as_of)} was replaced by circular item {v.ref}: {v.text}",
                     RESOLVED, [(CIRC, v.ref), (MASTER, ref)], "Circular item replaces the Master clause from its effective date.")
    return _resp(f"Clause {ref} (in force on {fmt_date(as_of)}): {v.text}", ANSWERED, [(MASTER, ref)])


def h_card_mdr(q, ctx, as_of, hol):
    if "card" in q and re.search(r"\b(mdr|discount rate|fee|fees|charge|charges)\b", q) and "upi" not in q \
            and not re.search(r"settl|when", q):
        return _resp("The documents define MDR only for UPI transactions (Master 2.1-2.3). They give no card MDR, "
                     "so I cannot answer this.", CANNOT, [])


def h_closure(q, ctx, as_of, hol):
    if not re.search(r"\bclos(e|ed|es|ing|ure)\b", q):
        return None
    cdate = None
    if "yesterday" in q:
        cdate = as_of - timedelta(days=1)
    elif re.search(r"\btoday\b", q):
        cdate = as_of
    elif (m := re.search(r"(\d+)\s+days?\s+ago", q)):
        cdate = as_of - timedelta(days=int(m.group(1)))
    if re.search(r"notice|any ?time|can i close", q) and cdate is None:
        return _resp("Yes. The merchant must give 30 days' written notice (5.1). The FAQ says the same.", ANSWERED,
                     [(MASTER, "5.1"), (FAQ, "Q5")])
    rule = ("Pending settlements are released within 10 working days of closure, after deducting outstanding dues "
            "(5.2). The FAQ's \"10 days\" is imprecise: it omits 'working' and the deduction of dues.")
    how = "FAQ (Mar 2026) is a summary; Master 5.2 is authoritative on the exact period and on the dues deduction."
    cites = [(MASTER, "5.2"), (MASTER, "5.1"), (FAQ, "Q5")]
    if cdate is None:
        return _resp(rule + " Tell me the closure date and I can compute the latest release date.", RESOLVED, cites, how)
    deadline = calc.nth_working_day_after(cdate, 10, hol)
    hol_txt = ("Supplied bank holidays were excluded." if hol else
               "Only Sundays are excluded; the documents give no bank-holiday calendar, so any bank holiday in "
               "between pushes this later")
    ans = (f"{rule} For a closure on {fmt_date(cdate)}, 10 working days (counting from the next day) ends on "
           f"{fmt_date(deadline)}. {hol_txt}. One caution: closure normally needs 30 days' written notice (5.1), "
           f"so a closure effective {fmt_date(cdate)} is only valid if notice was given by "
           f"{fmt_date(cdate - timedelta(days=30))}.")
    return _resp(ans, RESOLVED, cites, how, {"closure": str(cdate), "release_deadline": str(deadline)})


def h_windows(q, ctx, as_of, hol):
    if "chargeback" in q:
        return _resp("Chargeback disputes must be raised by the customer's bank within 120 days (3.4).", ANSWERED, [(MASTER, "3.4")])
    if "refund" in q and re.search(r"how long|how many days|deadline|time limit|window|last date|by when", q):
        return _resp("A merchant may initiate a refund within 90 days of the original transaction (3.1).", ANSWERED, [(MASTER, "3.1")])


def h_refund(q, ctx, as_of, hol):
    if not re.search(r"\brefund", q) or not re.search(r"\b(mdr|fee|fees|back|revers\w*|return\w*)\b", q):
        return None
    hours = None
    if re.search(r"same day|immediately|right away", q):
        hours = Decimal(1)
    elif (m := re.search(r"(\d+(?:\.\d+)?)\s*(minute|min|hour|hr|day)s?", q)):
        hours = Decimal(m.group(1)) * {"min": Decimal(1) / 60, "minute": Decimal(1) / 60, "hour": 1, "hr": 1, "day": 24}[m.group(2)]
    if as_of >= EFF_SEP:
        return _resp(f"No. On {fmt_date(as_of)} the MDR on a refunded transaction is not returned, whatever the timing. "
                     "Circular item D deleted clause 3.3 (the 24-hour reversal) from 1 Sep 2026, and 3.2 now applies "
                     "without exception. The FAQ's \"yes, within 24 hours\" is out of date.", RESOLVED,
                     [(CIRC, "D"), (MASTER, "3.2"), (MASTER, "3.3"), (FAQ, "Q3")],
                     "Circular item D (effective 1 Sep 2026) supersedes Master 3.3 and the March FAQ.")
    note = " This changes from 1 Sep 2026, when circular item D deletes the 24-hour reversal." if as_of >= CIRC_ISSUED else ""
    cites = [(MASTER, "3.2"), (MASTER, "3.3"), (FAQ, "Q3")] + ([(CIRC, "D")] if note else [])
    if hours is None:
        ans = (f"On {fmt_date(as_of)}: yes if the refund is initiated within 24 hours of the transaction (3.3, reversed in "
               f"full); otherwise the MDR is not returned (3.2).{note}")
    elif hours <= 24:
        ans = (f"Yes. A refund initiated within 24 hours is covered by clause 3.3, so the MDR is reversed in full "
               f"(on {fmt_date(as_of)}).{note}")
    else:
        ans = f"No. Outside the 24-hour window, clause 3.2 applies and the MDR is not returned.{note}"
    return _resp(ans, ANSWERED, cites)


def h_faq_mdr(q, ctx, as_of, hol):
    if "faq" not in q or not re.search(r"\b(cap|upper limit|mdr|fee|fees)\b", q):
        return None
    (rs, _), (cs, _), (cl, _) = (calc.param(n, as_of) for n in ("rate_small", "cap_small", "cap_large"))
    changed = rs != Decimal("0.003")
    ans = ("The FAQ (last updated 12 Mar 2026) says UPI MDR is 0.30% for small and 0.50% for large merchants and that "
           "\"there is no upper limit on the fee\". That last claim is wrong: Master 2.3 caps MDR on any single UPI "
           f"transaction (GST is charged on top, 2.4). On {fmt_date(as_of)} the cap is {inr(cs)} for merchants up to "
           f"₹10 lakh monthly and {inr(cl)} above that" + (" (circular item C)" if as_of >= EFF_AUG else "") + ". "
           + (f"The FAQ's small-merchant 0.30% is also stale: it is {rs * 100:.2f}% since 1 Aug 2026 (item B)." if changed else ""))
    cites = [(FAQ, "Q2"), (MASTER, "2.3"), (MASTER, "2.4"), (MASTER, "2.1")] + ([(CIRC, "C"), (CIRC, "B")] if changed else [])
    return _resp(ans.strip(), RESOLVED, cites,
                 "The FAQ is a non-authoritative summary written before the policy changes; the policy and circular prevail.")


def h_settlement(q, ctx, as_of, hol):
    if amounts(q) or not re.search(r"settl|\bwhen\b.*\b(receive|get|credited|money|paid)|payout|credited", q):
        return None
    card = "card" in q
    upi = "upi" in q or not card
    same = re.search(r"same[- ]day|instant|t\+0|immediate", q)
    parts, cites, status, how = [], [], ANSWERED, None
    if card:
        if same:
            parts.append("No. Card transactions settle T+2 (1.2). The circular's same-day option (item A) covers UPI only "
                         "and item F leaves 1.2 unchanged, so the policy gives no same-day card settlement.")
            cites += [(MASTER, "1.2"), (CIRC, "A"), (CIRC, "F")]
        else:
            parts.append("Card transactions settle T+2 (1.2); the circular does not change this.")
            cites += [(MASTER, "1.2"), (FAQ, "Q1")]
    if upi:
        nxt = calc.nth_working_day_after(as_of, 1, hol)
        if as_of >= EFF_AUG:
            parts.append(f"As of {fmt_date(as_of)}, UPI settlement is T+0 (same day, by 11:59 PM) only for merchants with an "
                         "active \"Instant Settlement\" add-on, and T+1 (next working day) for everyone else (circular item A). "
                         f"Merchant size does not matter. The documents do not say whether this merchant has the add-on, so "
                         f"without it a payment on {fmt_date(as_of)} settles on {fmt_date(nxt)} (Sundays and bank holidays "
                         "are not working days; no holiday calendar is provided).")
            cites += [(CIRC, "A"), (MASTER, "1.1"), (MASTER, "1.3"), (FAQ, "Q1")]
            status, how = RESOLVED, "Circular item A (effective 1 Aug 2026) replaces Master 1.1; the March FAQ does not mention the add-on."
        elif same:
            parts.append(f"No, same-day UPI settlement is not available on {fmt_date(as_of)}: UPI settles T+1 (1.1). The circular "
                         "that introduces T+0 was issued 20 Jul 2026 but only takes effect on 1 Aug 2026.")
            cites += [(MASTER, "1.1"), (CIRC, "A")]
            if as_of >= CIRC_ISSUED:
                status, how = RESOLVED, "Circular issued but not yet effective; Master 1.1 still governs."
        else:
            parts.append(f"UPI settlement is T+1, the next working day (1.1, 1.3); Sundays and bank holidays are excluded.")
            cites += [(MASTER, "1.1"), (MASTER, "1.3"), (FAQ, "Q1")]
    return _resp(" ".join(parts), status, cites, how)


LIMIT_RE = re.compile(r"twice|two times|\b\d+ times|two payments|daily|per day|\bin a day|\bin one day|\bin the same day|"
                      r"maximum|\blimit\b|at most|how much can|"
                      r"\bcan (?:a |the |any )?(?:customer|buyer|i|we|merchant|they)\b.*\b(?:pay|accept)")


def h_limit(q, ctx, as_of, hol):
    if not LIMIT_RE.search(q):
        return None
    amts = amounts(q)
    amt = amts[-1] if amts else None
    ins = re.search(r"insurance|capital market", ctx)
    n = 2 if re.search(r"twice|two times|two payments", q) else (int(m.group(1)) if (m := re.search(r"\b(\d+) times", q)) else 1)
    daily_cites = [(MASTER, "4.3")] + ([(CIRC, "E")] if as_of >= EFF_AUG else [])
    daily_txt = ("₹1,00,000 per customer account across all UPI transactions, or the limit set by the customer's own bank if "
                 "lower (4.3 as amended by item E)" if as_of >= EFF_AUG else
                 "₹1,00,000 per customer account across all UPI transactions (4.3)")
    if amt is None:
        ans = (f"The per-transaction UPI limit is ₹1,00,000 (4.1). Capital Markets and Insurance merchants may accept up to "
               f"₹2,00,000 per transaction, but only after completing enhanced KYC (4.2, 4.4). Separately, the daily limit is {daily_txt}.")
        if ins:
            return _resp(ans + " The FAQ states the ₹2,00,000 figure without the enhanced-KYC condition.", RESOLVED,
                         [(MASTER, "4.1"), (MASTER, "4.2"), (MASTER, "4.4"), (FAQ, "Q4")] + daily_cites,
                         "FAQ omits the enhanced-KYC condition; Master 4.4 is authoritative.")
        return _resp(ans, ANSWERED, [(MASTER, "4.1"), (MASTER, "4.2"), (MASTER, "4.4"), (FAQ, "Q4")] + daily_cites)
    if amt > ENHANCED:
        return _resp(f"No. {inr(amt)} exceeds even the enhanced ₹2,00,000 per-transaction limit (4.1, 4.2, 4.4).", ANSWERED,
                     [(MASTER, "4.1"), (MASTER, "4.2"), (MASTER, "4.4")])
    if amt > PER_TXN:
        if ins:
            return _resp(f"I cannot give a reliable answer. 4.2 allows Capital Markets/Insurance merchants with enhanced KYC (4.4) "
                         f"up to ₹2,00,000 per transaction, but 4.3 also sets a daily limit of {daily_txt}, and the documents do "
                         "not say which prevails for these merchants.", CANNOT,
                         [(MASTER, "4.2"), (MASTER, "4.4")] + daily_cites)
        return _resp(f"No. {inr(amt)} exceeds the ₹1,00,000 per-transaction limit (4.1). Only Capital Markets/Insurance merchants "
                     "with enhanced KYC may accept more (4.2, 4.4).", ANSWERED, [(MASTER, "4.1"), (MASTER, "4.2"), (MASTER, "4.4")])
    total = amt * n
    if total > PER_TXN:
        return _resp(f"No. Each {inr(amt)} payment is within the ₹1,00,000 per-transaction limit (4.1), but the daily limit is "
                     f"{daily_txt}. The first payment goes through; the second would take the day's total to {inr(total)} and "
                     "would be declined. (If the customer's own bank limit is lower, even the first may fail.)", ANSWERED,
                     [(MASTER, "4.1")] + daily_cites, calc_={"payments": n, "total": str(total), "daily_limit": "100000"})
    return _resp(f"Yes. {inr(total)} is within the per-transaction limit (4.1) and the daily limit ({daily_txt}).", ANSWERED,
                 [(MASTER, "4.1")] + daily_cites)


def h_fee(q, ctx, as_of, hol):
    amts = amounts(q)
    if not amts or not re.search(r"\b(mdr|gst|fee|fees|charge|charges|pay|cost|deduct\w*|how much)\b", q):
        return None
    amt, size = amts[-1], _size(ctx)
    premise = ""
    if re.search(r"\bcap\b.*(removed|scrapped|abolished|eliminated|waived)|(removed|scrapped|abolished|eliminated)\b.*\bcap\b", q):
        premise = "The cap was not removed: circular item C kept it and set it at ₹25 for merchants above ₹10 lakh. "
    cites = []
    if amt > ENHANCED:
        return _resp(f"{inr(amt)} exceeds every UPI per-transaction limit (₹1,00,000, or ₹2,00,000 with enhanced KYC), so it cannot "
                     "be a single UPI transaction and no fee applies.", ANSWERED, [(MASTER, "4.1"), (MASTER, "4.2"), (MASTER, "4.4")])
    lines, amended, large_capped, results = [], False, False, []
    for s in ([size] if size else ["small", "large"]):
        r = calc.mdr_for(amt, s, as_of)
        results.append(r)
        cites += r["cites"]
        amended |= any(d == CIRC for d, _ in r["cites"])
        large_capped |= (s == "large" and r["capped"])
        cap_txt = f", capped at {inr(r['cap'])}" if r["capped"] else ""
        lines.append(f"{s.capitalize()} merchant: MDR {r['rate'] * 100:.2f}% of {inr(amt)} = {inr(r['raw_mdr'])}{cap_txt}, so MDR = "
                     f"{inr(r['mdr'])}; GST 18% on the MDR = {inr(r['gst'])} (not part of the cap); total {inr(r['total'])}.")
    pre = ""
    if amt > PER_TXN:
        pre = (f"Note: {inr(amt)} is above the ₹1,00,000 per-transaction UPI limit (4.1). Only Capital Markets/Insurance merchants "
               "with enhanced KYC may accept up to ₹2,00,000 (4.2, 4.4); for anyone else this payment would be declined. "
               "If it is accepted, the fee is: ")
        cites += [(MASTER, "4.1"), (MASTER, "4.2"), (MASTER, "4.4")]
    hist = ""
    if as_of >= EFF_AUG and size:
        old = calc.mdr_for(amt, size, date(2026, 7, 31))
        if old["mdr"] != results[0]["mdr"]:
            hist = f" (Before 1 Aug 2026 the same payment cost MDR {inr(old['mdr'])} + GST {inr(old['gst'])}.)"
    if not size:
        lines.append("You did not say whether the merchant is small (up to ₹10 lakh a month) or large, so both are shown.")
    conflict = amended or large_capped
    how = None
    if conflict:
        cites.append((FAQ, "Q2"))
        how = ("Circular item(s) effective 1 Aug 2026 supersede the Master clause; " if amended else "") + \
              "the FAQ's \"no upper limit on the fee\" is wrong, as Master 2.3 / item C cap the MDR."
    return _resp(premise + pre + " ".join(lines) + hist, RESOLVED if conflict else ANSWERED, cites, how,
                 [{k: str(v) for k, v in r.items() if k != "cites"} for r in results])


def h_gst(q, ctx, as_of, hol):
    if re.search(r"\bgst\b", q) and not amounts(q):
        return _resp("GST at 18% is charged on the MDR amount (not on the transaction value) and is not part of the MDR cap (2.4).",
                     ANSWERED, [(MASTER, "2.4")])


HANDLERS = [h_clause, h_card_mdr, h_closure, h_windows, h_refund, h_faq_mdr, h_settlement, h_limit, h_fee, h_gst]


def _to_date(d):
    if isinstance(d, datetime):
        return d.date()
    return d if isinstance(d, date) else date.fromisoformat(d)


def ask(question, as_of_date="2026-08-15", context=None, holidays=()):
    """context: optional earlier question, for follow-ups like 'same merchant'."""
    as_of = _to_date(as_of_date)
    q = question.lower()
    ctx = f"{(context or '').lower()} {q}"
    if as_of < docs.MASTER_EFFECTIVE:
        out = _resp(f"No policy was in force on {fmt_date(as_of)}: the Master Document is effective from 1 Jan 2026.", CANNOT, [])
    else:
        out = None
        for h in HANDLERS:
            out = h(q, ctx, as_of, tuple(holidays))
            if out:
                break
        if out is None:
            out = _resp("I could not match this question to anything the three documents cover, so I will not guess.", CANNOT, [])
    out["as_of_date"] = as_of.isoformat()
    return out
