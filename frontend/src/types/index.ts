export interface Scenario {
  id: string;
  name: string;
  icon: string;
  tag: string;
  prompt: string;
  description: string;
  normalized_request: {
    request_id: string;
    product_query: string;
    quantity: number;
    max_budget_paise: number;
    currency: string;
    max_delivery_days: number;
    hard_specs: {
      min_ram_gb: number;
      min_cpu_tier: string;
      min_storage_gb: number;
    };
    mandate_id: string;
  };
}

export interface GateResult {
  gate: string;
  validation_target: string;
  status: "PASS" | "FAIL" | "PENDING";
  expected: string;
  actual: string;
  reason: string;
  metadata?: Record<string, any>;
}

export interface OfferItem {
  sku: string;
  name: string;
  category: string;
  quantity: number;
  unit_price_paise: number;
  total_price_paise: number;
  unit_cost_paise: number;
  total_cost_paise: number;
  is_overstock?: boolean;
}

export interface FormattedOffer {
  offer_id: string;
  transaction_id: string;
  strategy: string;
  explanation: string;
  total_price_paise: number;
  catalog_price_paise: number;
  margin_percent: number;
  discount_percent: number;
  final_score: number;
  items: OfferItem[];
}

export interface CandidateStrategy {
  strategy: string;
  name: string;
  total_price_paise: number;
  margin_percent: number;
  discount_percent: number;
  score: number;
  status: "WINNER" | "ALTERNATIVE" | "REJECTED_MARGIN";
  note: string;
  gate_failure_reason?: string;
}

export interface AuditEventItem {
  id?: string | number;
  timestamp: string;
  component: string;
  event_type: string;
  status: "INFO" | "PASS" | "WARN" | "FAIL";
  message: string;
  metadata?: Record<string, any>;
}

export interface SimulationResult {
  transaction_id: string;
  rescued: boolean;
  outcome_type?: "DIRECT_MATCH" | "RESCUED_COUNTEROFFER" | "REJECTED";
  direct_match?: boolean;
  offer: FormattedOffer | null;
  gate_results: GateResult[];
  message: string;
  candidates: CandidateStrategy[];
  catalog_price_paise: number;
  buyer_decision: {
    status: "ACCEPTED" | "REJECTED" | "COUNTER";
    reason: string;
    mandate_compliant: boolean;
  };
}

export interface BuyerMandate {
  mandate_id: string;
  max_budget_paise: number;
  currency: string;
  max_delivery_days: number;
  allowed_categories: string[];
  expires_at: string;
}

export interface IntentIntelligence {
  product_query: string;
  quantity: number;
  max_budget_paise: number;
  currency: string;
  max_delivery_days: number | null;
  hard_specs: {
    min_ram_gb?: number;
    min_cpu_tier?: string;
    min_storage_gb?: number;
  };
  preferences: string[];
  recommended_strategies: string[];
  strategy_rationale: string;
  confidence: number;
  provider: string;
  model?: string | null;
  fallback_reason?: string | null;
}
