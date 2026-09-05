# Phase 7 — Gemini Flash Agents and Project Completion

## Status

Implementation and automated verification complete on 2026-09-04. Runtime
activation is controlled by the local `backend/.env` configuration.

## Model

ASC uses `gemini-3.5-flash` through the Google Gemini `generateContent` REST API.
The provider sends the key through the `x-goog-api-key` header and requests JSON
output for intent extraction. The free tier is suitable for development subject
to Google's current account, region, quota, and data-use terms.

## Configuration

```dotenv
ASC_LLM_PROVIDER=gemini
ASC_LLM_MODEL=gemini-3.5-flash
ASC_LLM_TIMEOUT_SECONDS=20
GEMINI_API_KEY=your_key_from_google_ai_studio
```

Only `GEMINI_API_KEY` is missing from the checked local setup. Restart FastAPI
after adding it. Never expose the key to Next.js or commit `backend/.env`.

## Agent responsibilities

Gemini may:

- identify explicitly supplied procurement fields;
- ask for missing product, quantity, or maximum budget;
- normalize complete natural-language intent into the validated
  `IntentIntelligence` schema;
- recommend only allow-listed strategy names;
- write the Merchant Agent's response using supplied deterministic facts.

Gemini may not calculate or authorize prices, discounts, margins, policy results,
inventory, payments, or offers. Invalid output, timeout, quota failure, or a missing
key falls back to the deterministic provider. Provider and model metadata stay
private backend diagnostics and are not shown in the Buyer Workspace.

## Catalog and clean state

The idempotent seed now contains 26 products across laptops, monitors, and
accessories. `scripts/reset_transaction_data.py --confirm` clears only deals,
agent messages, and audit events while preserving products and merchant policies.

## Verification

- Gemini request shape and structured schema are tested with a mocked HTTP call.
- Provider failure fallback and strategy allow-list tests remain active.
- Complete deal, rejection, recovery, inventory, and budget tests pass against a
  clean migrated database.
- Frontend lint, TypeScript validation, and production build pass for `/buyer`
  and `/merchant`.
