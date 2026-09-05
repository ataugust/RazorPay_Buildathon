<div align="center">

# ASC — Autonomous Sales Counterparty

### AI negotiates. Deterministic controls decide.

An agentic B2B commerce platform that turns natural-language purchase requests into
policy-safe, explainable and auditable transactions.

[![Frontend](https://img.shields.io/badge/Frontend-Next.js-111827?logo=nextdotjs)](frontend)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](backend)
[![Database](https://img.shields.io/badge/Database-SQLAlchemy-D71F00)](backend/app/db)
[![Intelligence](https://img.shields.io/badge/Intelligence-Gemini%20Flash-4F46E5)](backend/app/llm)
[![Control Plane](https://img.shields.io/badge/Control%20Plane-6%20Hard%20Gates-059669)](backend/app/control_plane)
[![CI](https://github.com/ataugust/RazorPay_Buildathon/actions/workflows/ci.yml/badge.svg)](https://github.com/ataugust/RazorPay_Buildathon/actions/workflows/ci.yml)

</div>

## The problem

LLM agents are powerful negotiators, but they are not safe commercial authorities.
An unconstrained agent can misunderstand quantities, invent discounts, or approve a
deal that destroys merchant margin.

ASC solves this with a deterministic **Commerce Control Plane**. Gemini Flash may
interpret intent, recommend bounded strategies and explain an outcome—but only
verified Python logic can calculate prices or authorize a transaction.

> **Core invariant:** AI proposes. The Control Plane decides.

## What makes ASC different

- **Two real counterparties:** separate Buyer Workspace and Merchant Console.
- **Clarification before assumption:** missing quantity or budget is requested, never invented.
- **Six hard controls:** margin, inventory, budget, discount, specifications and mandate.
- **Transaction rescue:** volume discounts, substitutions and overstock bundles recover at-risk sales.
- **Explainable decisions:** every pass or failure includes the rule, observed value and reason.
- **Persistent evidence:** deals, messages, offers and audit events share one SQLAlchemy database.
- **Bounded AI:** model failures fall back safely without bypassing commercial policy.
- **Payment demonstration:** a polished Razorpay-style demo flow completes with no real charge and updates inventory and revenue; server-verified Standard Checkout is also implemented for configured environments.

## System architecture

~~~mermaid
flowchart LR
    B[Buyer] --> BW[Buyer Workspace]
    BW --> BA[Buyer Agent]
    BA -->|Structured request| MA[Merchant Agent]
    MA --> C[Catalog & Inventory]
    MA --> S[Bounded Strategy Engine]
    S --> CP{Commerce Control Plane}
    CP --> G1[Margin]
    CP --> G2[Inventory]
    CP --> G3[Budget]
    CP --> G4[Discount]
    CP --> G5[Specifications]
    CP --> G6[Mandate]
    CP -->|All pass| O[Authorized offer]
    CP -->|Any fail| R[Rejected with evidence]
    O --> P[Razorpay Checkout]
    P --> D[(SQLAlchemy + SQLite)]
    D --> MC[Merchant Console]
    D --> A[Audit trail]
~~~

## Signature demo: recovering a deal

Use this prompt in the Buyer Workspace:

> I want to buy 10 units of MacBook Neo and my maximum budget is ₹7 lakhs.

The catalog total is ₹7.5 lakhs, so the initial transaction cannot pass the Budget
Gate. ASC deliberately does not hide this failure. The agents negotiate a bounded
recovery offer:

- 10 × Apple MacBook Neo at the catalog price: **₹7,50,000**
- 10 × overstock wireless mice included at no charge
- Revised buyer mandate required before checkout
- Offer evaluated across all six deterministic controls
- Successful demo payment marks the sale **Recovered** and updates merchant revenue

This demonstrates negotiation, policy enforcement, overstock utilization,
explainability and measurable business value in one flow.

## Product surfaces

| Buyer Workspace | Merchant Console |
| --- | --- |
| Natural-language purchase requests | Revenue and recovery KPIs |
| Targeted clarification questions | Live deals and transaction history |
| Merchant proposals and negotiation | Catalog and inventory visibility |
| Inline revisions and rejection feedback | Strategy performance |
| Purchase history and checkout | Six-gate Control Plane evidence |
| Buyer-safe progress updates | Agent messages and audit activity |

## Technology

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| API | FastAPI, Pydantic |
| Persistence | SQLAlchemy, Alembic, SQLite |
| Language intelligence | Gemini Flash with deterministic fallback |
| Decision authority | Deterministic Python Control Plane |
| Payments | Razorpay Standard Checkout integration + demo-safe simulation |

## Run locally

### Prerequisites

- Python 3.11+
- Node.js 20+

### 1. Backend

~~~powershell
cd backend
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

FastAPI startup automatically applies Alembic migrations and idempotently seeds
the catalog and active merchant policy.

### 2. Frontend

~~~powershell
cd frontend
npm install
npm run dev
~~~

Open:

- Buyer Workspace: http://127.0.0.1:3000/buyer
- Merchant Console: http://127.0.0.1:3000/merchant
- API documentation: http://127.0.0.1:8000/docs

The generated merchant passcode is stored locally in
backend/data/merchant-access.txt and is excluded from Git.

## Optional configuration

Secrets belong only in backend/.env.

~~~dotenv
ASC_LLM_PROVIDER=gemini
ASC_LLM_MODEL=gemini-3.5-flash
GEMINI_API_KEY=your_google_ai_studio_key

# Optional real Razorpay Standard Checkout
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
~~~

Without external credentials, language processing has a deterministic fallback and
checkout uses an explicitly labelled demo simulation. No real money is charged in
demo mode.

## Verification

From backend:

~~~powershell
python -m scripts.test_phase1_3_integration
python -m scripts.test_phase5
python -m scripts.test_synchronized_deal_flow
python -m scripts.test_buyer_boundary
python -m scripts.test_razorpay_checkout
~~~

From frontend:

~~~powershell
npm run lint
npm run build
~~~

## Repository guide

~~~text
backend/app/api/             Buyer, merchant, audit and commerce APIs
backend/app/asc/             Orchestration and deterministic strategies
backend/app/control_plane/   Six authoritative policy gates
backend/app/llm/             Bounded language intelligence
backend/app/db/              SQLAlchemy models, session and bootstrap
backend/migrations/          Alembic schema history
frontend/src/app/            Buyer and merchant routes
frontend/src/components/     Product workspaces and design system
docs/phases/                 Phase-by-phase implementation record
~~~

Read the complete [development phases](docs/phases/README.md) or the
[Razorpay checkout design](docs/phases/phase-10-razorpay-checkout/README.md).

## Safety and trust boundaries

- The LLM cannot set authoritative prices, margins, discounts or approval results.
- Every offer must pass all six deterministic gates.
- Buyer-facing responses omit merchant costs, policies and internal reasoning.
- Payment secrets never reach the frontend.
- Inventory is revalidated before fulfilment.
- The payment simulation is visibly labelled so it cannot be mistaken for a live charge.

## Built for the Razorpay Buildathon

ASC demonstrates how agentic commerce can move beyond chat into controlled business
execution: autonomous enough to recover revenue, deterministic enough to trust.

---

<div align="center">
Built by <a href="https://github.com/ataugust">@ataugust</a>
</div>
