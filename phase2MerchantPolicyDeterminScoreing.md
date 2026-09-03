# Walkthrough - Phase 2: Merchant Policy, Strategy Generators & Scoring Engine

We have built Phase 2: Commercial Strategy & Policy Engine inside `backend/`. This phase establishes database-driven merchant policies, candidate strategy generators, and a multi-objective deterministic scoring function.

---

## What We Implemented & Learned

### 1. Merchant Policy DB Model & Migration (`Step 1`)
- **File Created:** [merchant_policy.py](file:///d:/JOBS/RazorPay/ASC+Control%20Plane/backend/app/db/models/merchant_policy.py)
- **Alembic Migration:** `002_create_merchant_policies_table.py` (`alembic upgrade head`)
- **Key Concept:** Merchant policies define the commercial boundaries (`min_margin_percent`, `max_discount_percent`, `allow_bundles`, `allow_substitutions`) and scoring weights ($w_{\text{margin}}, w_{\text{revenue}}, w_{\text{overstock}}, w_{\text{discount\_penalty}}$).

### 2. Candidate Strategy Generators (`Step 2`)
- **Files Created:** [strategy_types.py](file:///d:/JOBS/RazorPay/ASC+Control%20Plane/backend/app/domain/strategy_types.py) & [candidate_generators.py](file:///d:/JOBS/RazorPay/ASC+Control%20Plane/backend/app/asc/candidate_generators.py)
- **Key Concept:** Instead of letting LLMs invent prices or discounts, python generators construct concrete financial candidate packages:
  1. `VolumeDiscountGenerator`: Calculates volume price adjustments up to target buyer budget caps.
  2. `OverstockBundleGenerator`: Pairs requested items with high-margin overstock accessories (`is_overstock = True`).
  3. `ProductSubstituteGenerator`: Finds alternative in-stock products in the same category if requested SKU price exceeds budget.

### 3. Deterministic Scoring Engine (`Step 3`)
- **File Created:** [scoring_engine.py](file:///d:/JOBS/RazorPay/ASC+Control%20Plane/backend/app/asc/scoring_engine.py)
- **Key Concept:** Mathematical objective scoring function that ranks all candidate offers:
  $$\text{Final Score} = (w_{\text{margin}} \cdot S_{\text{margin}}) + (w_{\text{rev}} \cdot S_{\text{rev}}) + (w_{\text{overstock}} \cdot S_{\text{overstock}}) - (w_{\text{disc}} \cdot S_{\text{disc}})$$
  - Candidates yielding profit margin below `min_margin_percent` are assigned a score of `0.00` (automatically failing `MarginGate`).

---

## Verification & Test Execution Output

We executed a simulated transaction rescue test (`python -m scripts.test_phase2`):
- **Scenario:** Buyer requests 20x Lenovo IdeaPad Pro 16 (`LAP-001`) with budget cap **Rs. 24,00,000**.
- **Normal Catalog Price:** 20x Rs. 1,25,000 = **Rs. 25,00,000** (Direct Match Fails!).

### Deterministic Ranking Results

```text
==================================================
PHASE 2 VERIFICATION: MERCHANT POLICY & SCORING
==================================================
Policy Name:         default_policy
Min Margin Floor:    15.0%
Max Discount Cap:    20.0%
Scoring Weights:     Margin=0.4, Revenue=0.3, Overstock=0.2, DiscountPenalty=0.1

Generated 3 candidate offer strategies.

DETERMINISTIC RANKING RESULTS:
---------------------------------------------------------------------------------------------------
RANK  | STRATEGY             | TOTAL (Rs.)  | MARGIN %  | DISCOUNT % | SCORE  
---------------------------------------------------------------------------------------------------
1     | VOLUME_DISCOUNT      | Rs. 2,400,000 | 16.67   % | 4.00     % | 36.27  
      Explanation: Applied 4.0% volume pricing discount on 20x Lenovo IdeaPad Pro 16 to align with target budget Rs. 2,400,000.
      Item Details: ['20x Lenovo IdeaPad Pro 16 (SKU: LAP-001)']

2     | PRODUCT_SUBSTITUTE   | Rs. 2,240,000 | 19.64   % | 0.00     % | 35.86  
      Explanation: Substituted with in-stock alternative HP ProBook 450 (SKU: LAP-002) fitting budget cap Rs. 2,400,000.
      Item Details: ['20x HP ProBook 450 (SKU: LAP-002)']

3     | BUNDLE_OVERSTOCK     | Rs. 2,310,000 | 12.81   % | 9.77     % | 0.00   
      Explanation: Bundled 20x Lenovo IdeaPad Pro 16 with overstock 20x Wireless Mouse at special bundle pricing.
      Item Details: ['20x Lenovo IdeaPad Pro 16 (SKU: LAP-001)', '20x Wireless Mouse (SKU: ACC-001)']

==================================================
WINNING STRATEGY SELECTED: VOLUME_DISCOUNT
Final Score: 36.27/100
Total Counteroffer Value: Rs. 2,400,000
==================================================
```

> [!NOTE]
> `BUNDLE_OVERSTOCK` generated a 12.81% margin offer, which fell below the 15.0% merchant policy floor. The scoring engine automatically scored it **0.00**, demonstrating how profit safety is prioritized over closing an unprofitable bundle!
