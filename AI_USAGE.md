\# AI usage



\## Tool

Claude (Anthropic), via chat. No other AI tools. No AI or network calls at runtime;

the system is rule-based, deterministic and offline.



\## Where AI was used

* Helped structure the code into separate modules for document parsing, calculations, and question handling.
* Generated and refined portions of the implementation.
* Assisted with preparing evaluation cases, debugging, and drafting documentation.



\## What I did myself

* Analysed the assignment requirements and identified key policy conflicts and effective-date rules.
* Decided on a deterministic, rule-based approach prioritising accuracy, traceability, and safe refusals.
* Reviewed the implementation against the source documents and expected answers.
* Tested the required questions and created additional evaluation cases, including adversarial scenarios.
* Investigated a paraphrasing failure, verified the fix, and documented limitations and design decisions.



\## Issues found while verifying

* A keyword bug where "within a day" matched "in a day" and gave a wrong limits answer,

&#x20; fixed with word boundaries (see in DECISIONS.md #16).

* The self-written eval (21/21) overstates real accuracy, see it in WHERE\_IT\_BREAKS.md.



\## Validation

The system passed all 8 required questions and all 21 evaluation cases, including 13 adversarial cases. Additional paraphrase testing revealed a bug that was subsequently fixed.

These results demonstrate consistency against the test set, not guaranteed accuracy for arbitrary questions. Known limitations are documented in WHERE\_IT\_BREAKS.md.



\## Reflection

AI helped accelerate development, but policy interpretation, design choices, and validation remained central to my work. The project reinforced the importance of deterministic calculations, date-aware rules, verifiable citations, and abstaining when the available evidence is insufficient.

