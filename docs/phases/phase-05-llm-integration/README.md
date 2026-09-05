# Phase 5 — Bounded Language Intelligence

Status: **Implemented and integration-tested**

Phase 5 adds natural-language understanding without moving commercial authority
into a probabilistic component. The intelligence layer extracts buyer intent,
classifies hard constraints and preferences, recommends an allow-listed strategy,
and explains that recommendation. Deterministic Python still creates every offer,
calculates every monetary value, ranks candidates, and runs the six Control Plane
gates.

## Runtime flow

```text
Natural-language prompt
→ configured intent provider
→ validated IntentIntelligence schema
→ BuyerRequest API schema
→ bounded strategy allow-list
→ deterministic candidate generators and scoring
→ deterministic Control Plane verdict
→ persisted audit trail
```

If a cloud or local model times out, returns invalid JSON, or violates the schema,
ASC automatically uses the rule-based provider. Provider failures never bypass the
Control Plane.

## Implemented components

- `backend/app/llm/contracts.py` — Pydantic contract for constraints,
  preferences, confidence, explanations, and allow-listed strategies.
- `backend/app/llm/providers.py` — provider interface, deterministic parser,
  configurable cloud JSON provider, and Ollama provider.
- `backend/app/llm/service.py` — provider selection and safe fallback.
- `backend/app/asc/intent_parser.py` — compatibility facade converting
  intelligence into `BuyerRequest`.
- `backend/app/asc/orchestrator.py` — consumes only bounded strategy names and
  records `INTENT_NORMALIZED` in the audit trail.
- `frontend/src/app/page.tsx` — displays provider, model, confidence, rationale,
  strategies, and the actual normalized request returned by the API. Its catalog
  narrative and candidate cards are also sourced from the live result rather than
  scenario fixtures. The trust-boundary divider is horizontally resizable.

The Phase 5 interface deliberately says `RULE-BASED • NO LLM CALL` when the
deterministic provider is active. It does not claim a buyer/merchant dialogue;
stateful agent-to-agent negotiation remains Phase 6.

## Configuration

Copy `backend/.env.example` into a local `.env` and choose one provider:

- `deterministic` — default; no network or credentials.
- `cloud` — configurable chat-completions-style JSON endpoint.
- `ollama` — local `/api/chat` endpoint.

Secrets belong only in `.env`; never commit them.

## Safety boundary

The intelligence provider may set only interpretation fields and values from
`AllowedStrategy`. Pydantic rejects invented strategy names. Provider output has
no fields for an authoritative price, discount, margin, approval, or payment.

The bounded vocabulary also includes `QUANTITY_ADJUSTMENT` and
`DELIVERY_TRADEOFF`, so the intelligence layer can classify those opportunities.
`DIRECT_MATCH` is determined from catalog price, stock, and buyer budget in Python.
The executable rescue generators remain `VOLUME_DISCOUNT`, `BUNDLE_OVERSTOCK`,
and `PRODUCT_SUBSTITUTE`; quantity and delivery proposals cannot produce an offer
until future deterministic generators and matching policy gates exist.

## Verification

From `backend`:

```powershell
python -m scripts.test_phase5
python -m scripts.test_phase1_3_integration
```

From `frontend`:

```powershell
npm run build
```

The Phase 5 suite verifies rich constraint extraction, safe fallback, schema
rejection of an invented strategy, audit visibility, and catalog-price direct
matching.
