"""Run the eight required questions and print the results."""
import json
from policy_qa import ask

Q2 = "A large merchant (above Rs.10 lakh monthly) receives a Rs.4,000 UPI payment. What MDR and GST do they pay?"
CASES = [
    ("Q1", "When does a small merchant receive UPI money?", "2026-08-15", None),
    ("Q2", Q2, "2026-08-15", None),
    ("Q3", "Same merchant, a Rs.1,50,000 payment. What do they pay?", "2026-08-15", Q2),
    ("Q4a", "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?", "2026-08-20", None),
    ("Q4b", "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?", "2026-09-05", None),
    ("Q5", "What does the FAQ say about the MDR cap, and is the FAQ right?", "2026-08-15", None),
    ("Q6", "Can a customer pay Rs.1,00,000 twice in one day to a merchant?", "2026-08-15", None),
    ("Q7", "I closed my account yesterday. When will I get my money?", "2026-08-15", None),
    ("Q8", "Does the policy allow me to settle card payments same day?", "2026-08-15", None),
]
if __name__ == "__main__":
    for qid, q, d, ctx in CASES:
        r = ask(q, d, context=ctx)
        print(f"\n=== {qid} (as of {d}) {r['status']}\nQ: {q}\nA: {r['answer']}")
        if r["resolution"]:
            print("How:", r["resolution"])
        print("Cites:", ", ".join(f"{c['document']}:{c['clause']}" for c in r["citations"]) or "none")
