# Phase 3 — Source of Truth: Commerce Control Plane & Policy Gates

> **Authoritative Specification & Architecture Contract**  
> *This document serves as the permanent source of truth for Phase 3. Other AI models, agents, and developers can reference this document to understand the Commerce Control Plane hard safety boundary, gate contracts, and audit logging persistence.*

---

## 1. Executive Summary & Core Philosophy

### Core Rule: **ASC Proposes. Control Plane Decides.**

```text
                  ASC Engine
                      │
                      ▼
               Candidate Offer
                      │
                      ▼
         ┌─────────────────────────┐
         │   COMMERCE CONTROL PLANE│
         └─────────────────────────┘
          │    │    │    │    │    │
          ▼    ▼    ▼    ▼    ▼    ▼
        Margin Stock Budget Disc Spec Mandate
        Gate   Gate  Gate   Gate Gate Gate
          │    │    │    │    │    │
          └────┴────┴────┴────┴────┘
                      │
                      ▼
               APPROVE / REJECT
             + Structured Audit Log
```

* **Probabilistic AI (LLMs / Strategy Generators)** constructs candidate offers, explanations, and negotiation strategies.
* **Deterministic Control Plane (Python Hardened Code)** enforces strict profit margin floors, inventory checks, budget ceilings, policy discount caps, hardware specification bounds, and buyer agent authorization mandates.
* **Audit Persistence:** Every single gate check produces a structured `PASS` or `FAIL` record stored in the SQLite `audit_events` table.

---

## 2. Directory & Module Structure

```text
backend/
├── app/
│   ├── audit/
│   │   └── audit_service.py              # Persistent SQLite Audit Log Service
│   ├── control_plane/
│   │   ├── base_gate.py                  # Abstract Base Class BaseGate
│   │   ├── budget_gate.py                # 1. BudgetGate (offer_total <= max_budget)
│   │   ├── control_plane_engine.py       # Orchestrator running all 6 gates
│   │   ├── discount_gate.py              # 2. DiscountGate (discount % <= policy max)
│   │   ├── gate_result.py                # Standardized GateResult JSON schema
│   │   ├── inventory_gate.py             # 3. InventoryGate (qty <= DB stock_quantity)
│   │   ├── mandate_gate.py               # 4. MandateGate (Agent authorization bounds)
│   │   ├── margin_gate.py                # 5. MarginGate (margin % >= min_margin)
│   │   └── specification_gate.py        # 6. SpecificationGate (Hardware specs validation)
│   └── db/
│       └── models/
│           └── audit_event.py            # SQLAlchemy AuditEvent DB Model
├── migrations/
│   └── versions/
│       └── 003_create_audit_events_table.py # Alembic Migration
└── scripts/
    └── test_phase3.py                    # Verification Test Suite
```

---

## 3. Standardized Gate Output Contract

Every gate check produces a standardized `GateResult` JSON payload conforming to the Buildathon explainable AI requirement:

```json
{
  "gate": "MARGIN_GATE",
  "status": "FAIL",
  "expected": ">= 15.0%",
  "actual": "12.81%",
  "reason": "Offer violates merchant minimum profit margin (12.81% < >= 15.0%).",
  "metadata": {
    "margin_percent": 12.81,
    "min_margin_percent": 15.0
  }
}
```

---

## 4. The 6 Control Plane Gates

### 1. `MarginGate` (`margin_gate.py`)
* **Rule:** `candidate.margin_percent >= policy.min_margin_percent`
* **Purpose:** Guarantees that no discount or bundle proposal violates merchant profit floors (e.g. 15.0%).

### 2. `InventoryGate` (`inventory_gate.py`)
* **Rule:** `item.quantity <= product.stock_quantity` for every item line.
* **Purpose:** Verifies real-time stock availability directly against SQLite database inventory.

### 3. `BudgetGate` (`budget_gate.py`)
* **Rule:** `candidate.total_price_rupees <= max_budget_rupees`
* **Purpose:** Ensures the offer total fits within the buyer's maximum authorized budget cap.

### 4. `DiscountGate` (`discount_gate.py`)
* **Rule:** `candidate.discount_percent <= policy.max_discount_percent`
* **Purpose:** Prevents unauthorized price cuts exceeding merchant policy ceilings (e.g. 20.0%).

### 5. `SpecificationGate` (`specification_gate.py`)
* **Rule:** Substituted hardware items must satisfy hard spec constraints (`min_ram_gb`, `min_cpu_tier`, `min_storage_gb`).
* **Example:** If the buyer requests RAM $\ge$ 16GB, CPU $\ge$ i5, and Storage $\ge$ 512GB, ASC **must not** substitute an Acer laptop with 8GB RAM.
* **Sample Failure Output:**
  ```json
  {
    "gate": "SPECIFICATION_GATE",
    "status": "FAIL",
    "expected": "RAM >= 16GB",
    "actual": "8GB RAM",
    "reason": "Substituted product Acer Aspire Business (SKU: LAP-004) violates buyer RAM specification (8GB < 16GB).",
    "metadata": {
      "sku": "LAP-004",
      "expected_ram": 16,
      "actual_ram": 8
    }
  }
  ```

### 6. `MandateGate` (`mandate_gate.py`)
* **Rule:** Validates agentic purchase authorization payload (`max_amount`, `allowed_categories`, `expires_at`, `transaction_id`).
* **Purpose:** Ensures merchant execution stays strictly within the buyer agent's authorized transaction mandate bounds.

---

## 5. Audit Trail Database Persistence

All gate decisions and Control Plane engine verdicts are saved to the `audit_events` table in SQLite via `AuditService`.

### Database Schema (`audit_events`)

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer (PK) | Auto-increment primary key |
| `transaction_id` | String(100) (Indexed) | Unique transaction tracking ID |
| `timestamp` | DateTime (UTC) | Event timestamp |
| `component` | String(100) | Originating gate or module (e.g. `CONTROL_PLANE`, `SPECIFICATION_GATE`) |
| `event_type` | String(100) | Event type (e.g. `GATE_CHECK_PASS`, `CANDIDATE_APPROVED`) |
| `status` | String(20) | Result status (`PASS`, `FAIL`, `INFO`, `WARN`) |
| `message` | Text | Human-readable explanation string |
| `metadata_json` | JSON | Structured gate evaluation metrics |

---

## 6. How to Run Phase 3 Verification

```bash
cd backend

# 1. Run Alembic migration
.\venv\Scripts\alembic upgrade head

# 2. Run Phase 3 verification suite
.\venv\Scripts\python -m scripts.test_phase3
```
