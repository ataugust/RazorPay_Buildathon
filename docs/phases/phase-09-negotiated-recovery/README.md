# Phase 9 — Negotiated Recovery Demo

## Status

Implemented and regression-tested on 2026-09-05.

## Demo scenario

```text
10 × Apple MacBook Neo
Original budget: ₹7,00,000
Catalog total: ₹7,50,000
Negotiated addition: 10 × ASC Wireless Mouse at no charge
Included catalog value: ₹15,000
Proposed revised mandate: ₹7,50,000
```

The initial offer cannot pass the original Budget Gate. The buyer may explicitly
start negotiation. ASC then builds an overstock bundle, persists the negotiation
messages and progress, and checks the bundle against all six controls using the
proposed revised mandate. The system never silently changes the buyer's budget.

The Buyer Workspace labels the budget increase, included value, and free line
item. Only the Razorpay payment button authorizes the revised amount. Phase 10
creates a Razorpay Order and verifies a captured payment before checkout
revalidates and decrements both the laptop and mouse inventory.

## Demo portfolio

`python -m scripts.seed_demo_history --confirm` replaces transaction test noise
with 38 clearly identified synthetic demonstration transactions: 28 recovered,
8 direct, and 2 lost. It preserves catalog and merchant-policy data. The Merchant
Dashboard visibly labels this history as a demo portfolio so it is not presented
as real customer revenue.

Always create a SQLite backup before running the command.

## Verification

`scripts.test_buyer_boundary` verifies the complete initial failure, negotiated
bundle, revised-budget consent, and atomic inventory decrement for both SKUs.
