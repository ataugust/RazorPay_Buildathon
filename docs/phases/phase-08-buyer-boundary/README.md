# Phase 8 — Buyer Boundary and Policy Demonstration

## Status

Implemented and regression-tested on 2026-09-05.

## Purpose

Make the two business roles operationally separate and make the trust claim
demonstrable: language models interpret and recommend, while deterministic code
alone authorizes commercial outcomes.

## Implemented flow

```text
Buyer-owned persistent draft
→ explicit structured requirements or targeted clarification
→ buyer-safe request payload
→ complete catalog and specification search
→ deterministic baseline and buyer-requested candidates
→ six Commerce Control Plane gates
→ concise fact-bound merchant reply
→ explicit buyer approval
→ atomic stock and policy revalidation
→ verified payment checkout and persistent history
```

## Buyer boundary

- `/buyer` uses a private HTTP-only buyer-session cookie.
- Requests remain owned by one session and cannot be read by another.
- Budgets distinguish `specified`, `no_limit`, and `not_provided`; no artificial
  upper limit is shown or stored as the buyer's mandate.
- Clarification and revisions update one draft without reinterpreting confirmed
  fields. Revisions invalidate the prior unaccepted offer and restart progress.
- Public responses omit models, providers, strategies, costs, margins, scores,
  gates, policies, and merchant intelligence.

## Merchant boundary

- `/merchant` requires a signed merchant session.
- Non-buyer `/api/*` routes are protected by backend middleware.
- The console receives structured requests and may inspect catalog, policy,
  candidates, gate evidence, audit events, and buyer rejection comments.

## Requested-discount demonstration

`requested_discount_percent` is an optional, validated request constraint. A
buyer request for 30% produces an exact deterministic candidate. With a 15%
merchant ceiling, the Discount Gate records expected `<= 15%`, actual `30%`,
and `FAIL`. That rejected candidate never crosses the buyer boundary. A separate
baseline candidate may be returned only after passing all six gates.

## Recovery and checkout

- Gemini timeout or invalid JSON falls back to deterministic parsing.
- Interrupted `PREPARING`, `SENT`, or `WAITING` drafts become retryable errors
  at startup.
- Approval starts a serialized transaction and rechecks offer state, catalog
  activity, stock, specifications, budget, margin, discount, and active policy.
- Phase 10 replaces the mock with server-created and server-verified Razorpay Checkout.

## Verification

- `python -m unittest scripts.test_buyer_boundary`
- `python -m unittest scripts.test_phase1_3_integration`
- `python -m unittest scripts.test_phase5`
- `python -m unittest scripts.test_synchronized_deal_flow`
- `npx tsc --noEmit`
- `npm run lint`
- `npm run build`

All database integration tests use isolated temporary SQLite files.
