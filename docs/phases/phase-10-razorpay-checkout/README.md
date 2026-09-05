# Phase 10 — Verified Razorpay Checkout

## Status

Implemented and regression-tested on 2026-09-05. Runtime checkout requires local
Razorpay API credentials.

## Buyer payment flow

```text
Buyer accepts an eligible proposal
→ backend revalidates offer, budget, policy, specifications and stock
→ backend creates a Razorpay Order for the authoritative paise amount
→ Buyer Workspace opens Razorpay Standard Checkout
→ successful Checkout returns payment id, order id and signature
→ backend verifies HMAC signature using the secret key
→ backend fetches the payment and requires matching order, amount, currency and captured status
→ backend locks and revalidates stock and policy again
→ inventory is decremented and the deal becomes COMPLETED
```

Closing or failing Checkout does not complete the deal and does not decrement
inventory. A pending payment can be resumed. The retired `/accept` mock endpoint
returns HTTP 410 so no frontend can silently bypass Razorpay.

## Configuration

Add Test Mode values to `backend/.env` and restart FastAPI:

```dotenv
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

The key id is intentionally sent to Checkout. The secret remains backend-only.
Use Razorpay Test Mode for the demo; switching to live payments is an operational
decision, not a code fallback.

## Authoritative files

- `backend/app/payments/base.py`
- `backend/app/api/buyer.py`
- `frontend/src/components/BuyerPortal.tsx`
- `backend/scripts/test_razorpay_checkout.py`

## Verification

- `python -m scripts.test_razorpay_checkout`
- `python -m scripts.test_buyer_boundary`
- `npm run lint`
- `npm run build`
