# The end-to-end workflow, in plain terms
1. **Synthetic orders** are generated per tenant (seeded simulator) and loaded through a contract-checked warehouse pipeline.
2. **Recipes** (bills of materials) turn sold dishes into expected ingredient consumption.
3. **Inventory** counts and receipts (synthetic) are compared with expected consumption; a detector flags weeks where usage ran far above the site's own baseline. The detector never reads the injected truth; it is scored against it.
4. A **forecast** estimates the next days of ingredient demand; a rules-based recommender proposes a reorder from the cheapest valid (synthetic) supplier quote.
5. The **agent** retrieves evidence through THE WEIR (every read is a recorded tool call; supplier-written text is labelled untrusted), writes an explanation, and proposes a purchase. A validation gate drops any claim that cites missing evidence or a number not in that evidence, and rejects proposals that differ from the recommendation or exceed caps.
6. The proposal becomes a **write call that THE WEIR holds** for a human. Roles without the procurement tool in their policy are blocked outright.
7. A **different, authorised person approves** the exact call. The approval expires, works once, and is bound to the call (quantity, supplier, quote, amount, recommendation).
8. The upstream re-validates and the ledger creates a **DRAFT purchase order** (the only state its schema can store). Nothing is transmitted.
9. Every step carries one **correlation id**; the ledger's audit trail is hash-chained.
