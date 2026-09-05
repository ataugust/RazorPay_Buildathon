# Phase 6 — Agent Messaging and Split Workspaces

## Status

Implemented and integration-tested on 2026-09-04.

## Purpose

Turn every commercial evaluation into an explicit, persistent exchange between
the Buyer Agent and Merchant Agent. A failed deal must produce a useful merchant
reply; it must never masquerade as a sent proposal.

## Runtime flow

```text
Buyer Agent purchase request
→ persistent PURCHASE_REQUEST message
→ deterministic catalog, inventory, candidate, and gate evaluation
→ Merchant Agent OFFER_AVAILABLE or explained unable-to-offer response
→ persistent merchant reply
→ Buyer Workspace and Merchant Console poll the same transaction state
```

## Merchant response contract

Responses use an explicit `response_type`:

- `OFFER_AVAILABLE`
- `CLARIFICATION_REQUIRED`
- `NO_INVENTORY`
- `BUDGET_TOO_LOW`
- `POLICY_REJECTED`
- `NO_FEASIBLE_OFFER`

The response also carries buyer budget, catalog and closest evaluated prices,
budget gap, inventory availability, whether a discount was attempted, failed
policy explanations, and suggested next actions.

## Persistence

- `backend/app/db/models/agent_message.py` stores sender, recipient, message type,
  content, reason code, metadata, and timestamp.
- `deals.merchant_response_json` stores the current structured merchant reply.
- Migration `006_add_agent_messages_and_merchant_response.py` owns both schema
  changes.
- `GET /api/deals/{transaction_id}/messages` returns the chronological exchange.

## Frontend boundaries

- `/buyer` is an independent Buyer Workspace with requests, clarification,
  merchant replies, proposals, decisions, and purchase history.
- `/merchant` is an independent Merchant Console with inventory, policies,
  candidates, audit events, transactions, and the message exchange.
- `/` redirects to `/buyer`.
- There is no in-page Buyer/Merchant toggle. Open the routes in separate browser
  windows or tabs; both remain synchronized through the backend.

When an offer is impossible, the Buyer Workspace explains whether inventory was
missing or the budget/policy was infeasible, displays the Merchant Agent's reply,
and offers actions to increase budget, reduce quantity, or allow alternatives.
These actions open an inline revision form inside the current deal rather than
returning the buyer to the initial chat screen.

## Invariant

Agent messages explain and coordinate. Deterministic Python remains the only
authority for product matching, monetary calculations, policy decisions, offer
approval, and payment authorization. A future LLM may produce natural-language
interpretation and dialogue only through these validated contracts.

## Verification

- `python -m scripts.test_synchronized_deal_flow`
- `python -m scripts.test_phase5`
- `python -m scripts.test_phase1_3_integration`
- `npm run lint`
- `npx tsc --noEmit`
- `npm run build`

The synchronized-flow suite specifically verifies that an impossible monitor
budget returns `BUDGET_TOO_LOW`, persists both agent messages, emits
`MERCHANT_RESPONSE_SENT`, and does not emit `PROPOSAL_SENT`.
