# ASC Development Phases

These files are the implementation record for coding agents. Read them in numeric order.

| Phase | Status | Document |
| --- | --- | --- |
| 1 — Foundation | Complete and consolidated | [Phase 1](phase-01-foundation/README.md) |
| 2 — Offer Engine | Implemented and regression-tested | [Phase 2](phase-02-offer-engine/README.md) |
| 3 — Control Plane | Implemented and integration-tested | [Phase 3](phase-03-control-plane/README.md) |
| 4 — Audit and Dashboard | Implemented and integration-tested | [Phase 4](phase-04-audit-dashboard/README.md) |
| 5 — Bounded Language Intelligence | Implemented and integration-tested | [Phase 5](phase-05-llm-integration/README.md) |
| 6 — Agent Messaging and Split Workspaces | Implemented and integration-tested | [Phase 6](phase-06-agent-messaging/README.md) |
| 7 — Gemini Flash Agents and Project Completion | Implemented; activation key pending | [Phase 7](phase-07-gemini-agents/README.md) |
| 8 — Buyer Boundary and Policy Demonstration | Implemented and regression-tested | [Phase 8](phase-08-buyer-boundary/README.md) |
| 9 — Negotiated Recovery Demo | Implemented and regression-tested | [Phase 9](phase-09-negotiated-recovery/README.md) |
| 10 — Verified Razorpay Checkout | Implemented; credentials required at runtime | [Phase 10](phase-10-razorpay-checkout/README.md) |

The verified Phase 1–3 flow is:

```text
FastAPI request
→ Pydantic BuyerRequest schema
→ SQLAlchemy catalog and policy lookup
→ deterministic candidate generation and scoring
→ six Control Plane gates
→ SQLAlchemy audit persistence
→ public audit retrieval for the same transaction
→ live SSE delivery to the operations dashboard
→ bounded intent intelligence with deterministic fallback
→ persisted buyer-agent/merchant-agent messages
→ explicit merchant outcome and synchronized split workspaces
→ Gemini Flash language agents with schema validation and deterministic fallback
→ server-created Razorpay Order and server-verified captured payment
```
