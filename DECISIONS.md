# Decisions

Every ambiguity I hit, what I chose, and why.

1. **Circular effective dates.** The header says effective 1 Aug 2026. The line "(Effective 01 September 2026.)" sits directly after item D. I applied it to D only. Items E and F come after it, but a bare date line belongs to the item above it, and applying it to E would silently change the daily limit answer. Item D therefore starts on 1 Sep; A, B, C, E start on 1 Aug.
2. **Issued is not effective.** Issued 20 Jul. For dates 20 Jul to 31 Jul the circular is mentioned but the master governs.
3. **Source precedence.** Circular > Master (once effective); Master/Circular > FAQ. The FAQ (12 Mar 2026) predates the circular and is a summary, so it is never authoritative when it differs. Such cases return `CONFLICT_RESOLVED` with the reason.
4. **Status semantics.** `CONFLICT_RESOLVED` when two sources disagree on the answer, or a superseded version must be set aside. `ANSWERED` when the answer is stable (e.g. Q6, where item E doesn't change the outcome, and Q4 on 20 Aug, where FAQ and policy agree).
5. **Q1 add-on.** Whether a merchant has "Instant Settlement" is not in any document. I answer conditionally (T+1 default, T+0 with add-on) rather than assume.
6. **Working days after item A.** Item A replaces 1.1, which contained the definition of working days (excludes Sundays and bank holidays). I assumed the definition survives (item F: others unchanged; 1.3 still depends on it). No bank-holiday calendar exists, so only Sundays are excluded unless the caller passes `holidays`, and the answer says so.
7. **Q2 cap.** 0.50% of 4,000 = 20, which exceeds the old cap (15) but not the new one (25). On 15 Aug the answer is 20 + 3.60 GST. I also state the pre-1-Aug figure (15 + 2.70) to make the date dependence visible.
8. **Q3 limits.** 1,50,000 exceeds the 1,00,000 per-transaction limit (4.1). Only Capital Markets/Insurance with enhanced KYC may exceed it (4.2, 4.4). I answer "not acceptable for a normal merchant" and show the hypothetical fee (cap 25 + GST 4.50 = 29.50) if the merchant qualifies.
9. **4.2 vs 4.3.** An eligible merchant may take 2,00,000 per transaction, yet 4.3 sets a 1,00,000 daily limit per customer across all UPI. Nothing says which wins, so a question hitting this returns `CANNOT_ANSWER`, not a guess.
10. **Q6.** Taken to mean the same customer account. First payment (exactly at the limit, allowed since the limit is "up to") passes; the second is declined by 4.3. Item E means a lower bank limit could block even the first.
11. **Refund timing (Q4).** "Within 24 hours" is inclusive of 24h. The rule that applies is the one in force on `as_of_date`, taken as the refund date. A sale before 1 Sep refunded after it is therefore treated under the new rule (policy is silent; see WHERE_IT_BREAKS).
12. **Q7.** "Yesterday" is `as_of_date - 1`. Working days count from the day after closure. The FAQ's "10 days" vs policy's "10 working days" (plus deduction of dues) is resolved to the policy. I also flag that closure requires 30 days' written notice, so a closure "yesterday" implies notice by 15 Jul.
13. **Merchant size boundary.** "Up to ₹10 lakh" is small; strictly above is large. If the size is not stated I show both rather than assume.
14. **Rounding.** Not specified anywhere. MDR and GST are each rounded half-up to the paisa. The cap applies to MDR before GST (2.4).
15. **No LLM.** Hand-written rules keep it offline and deterministic, and every line is explainable. The cost is paraphrase brittleness.
16. **Bug found by self-testing.** "within a day" matched my limits keyword "in a day", giving a confident wrong answer. Fixed with word boundaries; it now falls through to `CANNOT_ANSWER`.
