# ASC — Autonomous Sales Counterparty
## Project Context and Build Specification for Google Antigravity

Last updated: 2026-09-01

---

# 1. Project Identity

**Project name:** ASC — Autonomous Sales Counterparty

**Core idea:**
ASC is a merchant-side autonomous AI commerce system. It receives purchase intent from a buyer-side agent, evaluates whether a normal catalog offer can satisfy the request, and when a transaction is at risk, attempts to construct a commercially valid counteroffer.

The system combines:

- LLM semantic reasoning and negotiation
- Deterministic offer generation/calculation
- A deterministic Commerce Control Plane
- Merchant strategy and policy constraints
- Inventory awareness
- Razorpay Test Mode payment integration
- A complete audit trail

**Primary track:** Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce.

---

# 2. The Problem

Static merchant catalogs work poorly when an AI buyer's constraints do not exactly match the listed catalog.

Example:

Buyer wants:
- 20 Lenovo IdeaPad laptops
- Maximum budget: ₹25 lakh
- Delivery requirement: specified by the buyer

If the normal merchant price exceeds the budget, a static catalog returns:

    NO MATCH → TRANSACTION LOST → ₹0 revenue

A skilled B2B salesperson would instead explore whether a viable commercial arrangement exists.

ASC automates this merchant-side commercial reasoning.

---

# 3. One-Sentence Pitch

> An autonomous merchant-side AI sales counterparty that negotiates with buyer agents to rescue and close transactions while deterministic controls protect merchant profitability and policies.

---

# 4. Core Design Principle

## Probabilistic AI must not directly control money.

LLMs are used for:

- Understanding natural-language requests
- Identifying hard constraints versus preferences
- Selecting negotiation strategies
- Generating explanations and counteroffers
- Communicating with the buyer agent

Deterministic code is used for:

- Prices
- Costs
- Profit margins
- Inventory
- Budget limits
- Merchant policies
- Final offer validation
- Payment execution

The LLM can PROPOSE.

The deterministic system DECIDES whether a proposal is valid.

---

# 5. Two-Agent Architecture

We will build two logical agents.

## A. Buyer Agent

Represents an AI buyer.

It receives natural-language user intent such as:

> "Order 20 Lenovo IdeaPad laptops with a maximum budget of ₹25L."

Its responsibilities:

1. Understand/parse the user's purchase intent.
2. Convert the intent into a structured purchase request.
3. Hold a bounded purchase mandate for the demo.
4. Send the request to the merchant.
5. Evaluate offers/counteroffers.
6. Accept, reject, or request another offer.

The buyer agent is a DEMO AGENT, not necessarily a full autonomous personal assistant.

Example normalized request:

```json
{
  "request_id": "REQ-001",
  "items": [
    {
      "product_query": "Lenovo IdeaPad",
      "quantity": 20
    }
  ],
  "max_budget_paise": 250000000,
  "currency": "INR",
  "max_delivery_days": 7,
  "preferences": []
}
```

A demo mandate can be:

```json
{
  "mandate_id": "MANDATE-001",
  "type": "demo_purchase_mandate",
  "max_amount_paise": 250000000,
  "currency": "INR",
  "expires_at": "2026-09-02T12:00:00Z"
}
```

This is NOT a claim that we implemented the full AP2 protocol. It is a bounded authorization object inspired by the need for agent payment limits.

---

## B. Merchant Agent / ASC

The merchant side contains two concepts:

### Merchant Agent
The interface/counterparty that receives buyer requests and communicates offers.

### ASC
The merchant's intelligence for transaction rescue.

Workflow:

    Buyer request
        ↓
    Merchant checks direct catalog match
        ↓
    If viable:
        Direct offer
    Else:
        ASC activates
        ↓
    Select commercial strategies
        ↓
    Generate candidate offers
        ↓
    Control Plane validates candidates
        ↓
    Best valid counteroffer
        ↓
    Buyer Agent evaluates
        ↓
    Accept / Reject / Counter

For MVP simplicity, Merchant Agent and ASC can live in the same backend service.

---

# 6. Important Correction: LLM Does Not Need to Do Everything

Natural-language input can be converted to JSON in two ways.

## Option A — Rule-based / deterministic parser

Useful when requests are constrained.

Example:

"Order 20 Lenovo IdeaPad laptops with a maximum budget of 25L"

Regex/logic can extract:
- quantity = 20
- product = Lenovo IdeaPad
- budget = ₹25 lakh

This is simple and reliable for an MVP.

## Option B — LLM structured extraction

Useful for natural language such as:

"We need around twenty developer laptops. Budget is roughly 25 lakhs, but delivery within a week is absolutely non-negotiable."

An LLM can return a Pydantic/JSON schema:

- product
- quantity
- hard constraints
- soft preferences
- budget
- delivery requirement

### Recommended approach

Use an abstraction:

    IntentParser
        ├── RuleBasedIntentParser
        └── LLMIntentParser

Start with deterministic parsing for known demo scenarios if it speeds development.

Use an LLM parser for the final interactive demo to demonstrate natural-language understanding.

---

# 7. ASC Workflow

## Step 1 — Intent normalization

Natural language:

> Order 20 Lenovo IdeaPad laptops with a maximum budget of ₹25L.

Structured request:

- Product: Lenovo IdeaPad
- Quantity: 20
- Maximum budget: ₹25L
- Delivery constraint: optional/default
- Preferences: optional

## Step 2 — Direct merchant offer

Query inventory and calculate:

    normal_price × quantity

Check:

- Product availability
- Quantity
- Budget
- Delivery
- Merchant policy

If valid:

    DIRECT OFFER

If not:

    TRANSACTION AT RISK → ASC ACTIVATES

## Step 3 — ASC strategy selection

The LLM should choose from a bounded strategy vocabulary, not invent arbitrary financial actions.

Initial strategy set:

- DISCOUNT
- BUNDLE_OVERSTOCK
- ALTERNATIVE_PRODUCT
- QUANTITY_ADJUSTMENT
- DELIVERY_TRADEOFF

The LLM may explain:

> The requested SKU is slightly above budget. Explore permitted volume pricing and overstock bundles.

## Step 4 — Deterministic candidate generation

Normal code generates candidate offers.

Example candidates:

- 5% permitted discount
- Volume pricing tier
- Same requested laptop plus overstock accessories
- Alternative SKU only if buyer allows it
- Different delivery arrangement only if buyer allows it

The deterministic engine calculates every:

- selling price
- cost
- total
- margin
- stock usage

## Step 5 — Commerce Control Plane

Every candidate passes through gates.

### BudgetGate
Offer must be within the buyer's maximum authorized amount.

### MarginGate
Merchant margin must be above the configured floor.

### InventoryGate
All offered items must be available.

### PolicyGate
Discounts, bundles, restricted products and pricing rules must comply with merchant policy.

### MandateGate
Offer amount must not exceed the demo authorization limit and mandate must not be expired.

Only after all gates pass:

    OFFER APPROVED

## Step 6 — Negotiation

Buyer Agent can:

- ACCEPT
- REJECT
- COUNTER

Example:

Buyer:
    "₹25L is my maximum."

ASC:
    "Direct offer cannot fit that budget. I can offer an approved volume-price package."

The merchant must never violate hard policy just to close the sale.

## Step 7 — Payment

After buyer acceptance:

    Approved offer
        ↓
    Payment provider abstraction
        ↓
    Razorpay Test Mode
        ↓
    Order/payment workflow

---

# 8. The Commerce Control Plane

This is one of the most important parts of the project.

Architecture:

    LLM / Agent Proposal
             ↓
    ------------------------
       TRUST BOUNDARY
    ------------------------
             ↓
    Deterministic Control Plane
             ↓
    BudgetGate
    MarginGate
    InventoryGate
    PolicyGate
    MandateGate
             ↓
    APPROVED / REJECTED

The LLM must NOT be able to:

- Set arbitrary final prices
- Bypass margin requirements
- Change inventory
- Override merchant policies
- Execute payments directly

---

# 9. Audit Trail

Every important event generates an AuditEvent.

Example:

    [INTENT_PARSED]
    Buyer requests 20 Lenovo IdeaPad laptops.
    Maximum budget: ₹25L.

    [DIRECT_MATCH]
    FAILED — Normal catalog total exceeds buyer budget.

    [ASC_STRATEGY]
    Selected: permitted volume pricing.

    [CANDIDATE_GENERATED]
    Offer total: ₹24.8L.

    [GATE_CHECK: MARGIN]
    Margin: 18.2%.
    Floor: 15%.
    PASS.

    [GATE_CHECK: INVENTORY]
    20 laptops available.
    PASS.

    [OFFER_APPROVED]

    [PAYMENT_EXECUTION]
    Razorpay Test Mode order created.

Audit events power the live dashboard.

---

# 10. MVP Dashboard

Dual-screen layout.

## Left: A2A Conversation / Network

Show:

Buyer intent
    ↓
Normalized JSON request
    ↓
Merchant response
    ↓
Counteroffer
    ↓
Buyer decision

Do not expose private model chain-of-thought.

Show structured reasoning summaries instead.

## Right: Control Plane / Audit Trail

Live events:

- Intent parsed
- Direct match failed/succeeded
- Strategy selected
- Candidate generated
- Budget PASS/FAIL
- Margin PASS/FAIL
- Inventory PASS/FAIL
- Policy PASS/FAIL
- Offer approved/rejected
- Payment initiated

Also show a visual trust boundary:

    LLM CAN PROPOSE
    ----------------
    CONTROL PLANE DECIDES
    ----------------
    RAZORPAY EXECUTES

---

# 11. Demo Scenarios

We need at least five.

## Scenario 1 — Direct success

Buyer request exactly matches inventory and budget.

Expected:

    Direct offer → Gates pass → Buyer accepts → Payment

## Scenario 2 — Transaction rescue

Normal catalog offer fails buyer budget.

ASC constructs a valid commercial offer.

Expected:

    Direct match fails
        ↓
    ASC activates
        ↓
    Candidate generated
        ↓
    Gates pass
        ↓
    Deal rescued

## Scenario 3 — Negotiation

Buyer rejects initial offer.

Buyer agent counters.

ASC attempts another valid strategy.

Expected:

    Offer → Counter → New offer → Accept/reject

## Scenario 4 — Graceful impossible deal

Example:

Buyer requests 50 laptops for ₹20L.

All candidates violate merchant margin or other constraints.

Expected:

    Candidate generated
        ↓
    MarginGate FAIL
        ↓
    No valid offer
        ↓
    Graceful rejection

Important result:

    Merchant safety prioritized over a bad sale.

## Scenario 5 — Batch evaluation

Run 100 synthetic purchase requests.

Include:

- Direct matches
- Budget mismatch
- Inventory shortage
- Restricted discounts
- Impossible margins
- Negotiation cases

Compare:

    Static Merchant
    vs
    ASC Merchant

Metrics:

- Number of transactions closed
- Transactions rescued
- Revenue
- Profit
- Average margin
- Margin-policy violations (must be zero)
- Unauthorized/over-budget executions (must be zero)
- Failure handling outcomes

Do not cherry-pick one successful transaction as evidence.

---

# 12. Tech Stack

## Backend

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- SQLite initially

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- Server-Sent Events or WebSocket for live audit events

## LLM

Use an LLM provider abstraction.

Recommended for hackathon development:

    Cloud model for primary demo reliability
    +
    Optional local model fallback/privacy mode

Do not tightly couple ASC to one provider.

Example:

    LLMProvider
        ├── CloudProvider
        └── OllamaProvider

## Payments

- MockPaymentProvider during initial development
- Razorpay Test Mode for final integration

---

# 13. Local vs Cloud LLM

Do not make "entirely local" a goal by itself.

For a hackathon, priorities are:

1. Reliability
2. Structured output quality
3. Fast iteration
4. Demonstrable AI reasoning

A cloud model is generally preferable for the final demo if credentials/network access are available.

A local model is useful for:

- Development without API costs
- Privacy experiments
- Offline fallback

The architecture should support both.

---

# 14. Money Rules

Never use floating-point numbers for money.

Use integer paise.

Example:

    ₹25,00,000 = 250000000 paise

All calculations:

- product prices
- costs
- totals
- discounts

should use integers.

---

# 15. Initial Domain Models

Product:

- id
- name
- category
- selling_price_paise
- cost_price_paise
- stock
- discount_allowed

MerchantPolicy:

- min_margin_percent
- allow_discounts
- allow_bundles
- max_discount_percent

BuyerRequest:

- request_id
- requested items
- max_budget_paise
- max_delivery_days
- preferences
- mandate

Offer:

- offer_id
- transaction_id
- items
- total_price_paise
- total_cost_paise
- margin_percent
- strategy
- status

AuditEvent:

- timestamp
- transaction_id
- component
- event_type
- status
- message
- metadata

---

# 16. Proposed Repository Structure

asc/

    backend/
        app/
            main.py

            api/
                purchase.py
                offers.py
                transactions.py

            domain/
                models.py
                offers.py
                policies.py

            agents/
                buyer_agent.py
                merchant_agent.py

            asc/
                orchestrator.py
                strategy_generator.py
                intent_parser.py
                candidate_generator.py

            control_plane/
                engine.py
                base_gate.py
                budget_gate.py
                margin_gate.py
                inventory_gate.py
                policy_gate.py
                mandate_gate.py

            payments/
                base.py
                mock.py
                razorpay.py

            audit/
                service.py
                models.py

            db/
                database.py
                seed.py

    frontend/

---

# 17. Seven Development Phases

## Phase 1 — Project Skeleton

- Repository
- FastAPI
- Next.js
- SQLite
- Seed merchant inventory
- Basic API

## Phase 2 — Deterministic Offer Engine

Build:

    Purchase request
        ↓
    Inventory lookup
        ↓
    Direct match
        ↓
    Candidate offers

No LLM required yet.

## Phase 3 — Commerce Control Plane

Implement:

- BudgetGate
- MarginGate
- InventoryGate
- PolicyGate
- MandateGate

## Phase 4 — Audit Trail and Dashboard

Implement:

- AuditEvent persistence
- Live event stream
- Dual-screen dashboard
- Trust boundary visualization

## Phase 5 — LLM Integration

Add:

- Natural-language intent parsing
- Constraint extraction
- Strategy selection
- Structured explanations

The LLM only proposes bounded strategies.

## Phase 6 — Buyer/Merchant Negotiation

Implement:

- Buyer Agent
- Merchant Agent/ASC interaction
- Offer
- Counteroffer
- Acceptance/rejection

## Phase 7 — Razorpay Integration and Evaluation

Implement:

- Razorpay Test Mode payment flow
- 100 synthetic transaction benchmark
- Baseline comparison
- Final demo scenarios
- Graceful failure demo

---

# 18. Main Success Metric

The project must prove:

> ASC increases merchant revenue relative to a static catalog baseline while maintaining strict merchant safety constraints.

Potential metrics:

- Transactions closed
- Transactions rescued
- Incremental revenue
- Incremental profit
- Average margin
- Policy violations = 0
- Over-budget executions = 0
- Inventory violations = 0
- Graceful failure rate

---

# 19. What NOT to Build Initially

Do not begin with:

- Full AP2 implementation
- Full ACP/UCP implementation
- Real cryptographic mandate system
- LangChain-heavy architecture
- Vector database
- Microservices
- Kubernetes
- Complex authentication

Build a complete working vertical slice first.

---

# 20. Immediate Development Goal

The first working vertical slice:

    POST /purchase-request
        ↓
    Structured buyer request
        ↓
    Inventory lookup
        ↓
    Direct match / failure
        ↓
    Candidate offer
        ↓
    MarginGate
        ↓
    Audit event
        ↓
    JSON response

Only after this works should complexity be added.

---

# 21. Key Message for the Project

> AI agents can reason and negotiate, but deterministic systems must enforce commercial and financial boundaries.

ASC is not a chatbot that randomly gives discounts.

ASC is a merchant-side autonomous commercial counterparty that:

- understands buyer intent
- tries to rescue at-risk transactions
- constructs bounded offers
- respects merchant strategy
- cannot violate deterministic profit and policy constraints
- creates an auditable path to payment
