# Where it breaks

Three cases I do not trust the system with. All were checked by running it.

## 1. Paraphrased questions get `CANNOT_ANSWER` even when the documents answer them
`ask("If I give the money back to my buyer within a day, does the fee come back?", "2026-08-20")` returns `CANNOT_ANSWER`. The correct answer (yes, 3.3 reversal) is in the documents, but the refund rule needs the literal word "refund". The same applies to "How much do I pay per UPI transaction?" (no amount, no "MDR") and "Rs 4k" (amount format not parsed). Routing is keyword-based, so the failure mode is safe (refusal, no wrong answer) but unhelpful. An earlier version was worse: "within a day" matched my "in a day" limits keyword and produced a confident wrong answer about limits (fixed with word boundaries). This class of bug is the main reason not to trust the rules on unseen phrasing.

## 2. A transaction and its refund on opposite sides of an effective date
"Refunded 3 hours after sale", sale on 31 Aug, refund on 1 Sep: the system uses the refund date, so it says the MDR is not returned. The policy never says whether the rule at transaction time or at refund time governs. A fairer reading could be that a transaction made under 3.3 keeps that protection. The system also cannot know the sale date unless it is the same as `as_of_date`, so I would not rely on it for straddling cases.

## 3. Q7-type date answers depend on a holiday calendar the documents don't provide
For "closed yesterday" it says 26 Aug 2026, counting only Sundays as non-working. 15 Aug is a real national bank holiday, and other holidays may fall in the window, so the true date is probably later. The answer says "only Sundays are excluded", but a support agent could still quote 26 Aug to a merchant. Related: if 4.2 (₹2,00,000 enhanced limit) and 4.3 (₹1,00,000 daily limit) are meant to interact, the system returns `CANNOT_ANSWER` because the documents don't say.

## Also note
The eval set was written by the same person as the rules, so the 21/21 score measures consistency with my own reading, not accuracy on questions the reviewer will ask.
