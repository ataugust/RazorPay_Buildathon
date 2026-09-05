export type DealStatus =
  | "WAITING_FOR_BUYER"
  | "RECOVERING"
  | "RECOVERY_OFFER_SENT"
  | "COMPLETED"
  | "LOST";

export interface Intelligence {
  product_query: string;
  quantity: number;
  max_budget_paise: number;
  currency: "INR";
  max_delivery_days?: number | null;
  hard_specs: Record<string, string | number | null>;
  preferences: string[];
  recommended_strategies: string[];
  strategy_rationale: string;
  confidence: number;
  provider: string;
  model?: string | null;
}

export interface OfferItem {
  sku: string;
  name: string;
  category: string;
  quantity: number;
  unit_price_rupees: number;
  total_price_rupees: number;
  unit_cost_rupees: number;
  total_cost_rupees: number;
  is_overstock?: boolean;
}

export interface Offer {
  offer_id: string;
  transaction_id: string;
  strategy: string;
  explanation: string;
  total_price_paise: number;
  margin_percent: number;
  discount_percent: number;
  final_score: number;
  items: OfferItem[];
}

export interface Candidate {
  strategy: string;
  name: string;
  total_price_paise: number;
  total_cost_paise: number;
  margin_percent: number;
  discount_percent: number;
  score: number;
  status: "WINNER" | "ALTERNATIVE" | "REJECTED_MARGIN" | "REJECTED_POLICY";
  note: string;
  gate_results?: GateResult[];
}

export interface GateResult {
  gate: string;
  status: "PASS" | "FAIL";
  expected: string;
  actual: string;
  reason: string;
  metadata?: Record<string, unknown>;
}

export interface AuditEvent {
  id: number;
  timestamp: string;
  transaction_id: string;
  component: string;
  event_type: string;
  status: "INFO" | "PASS" | "WARN" | "FAIL";
  message: string;
  metadata: Record<string, unknown>;
}

export type MerchantResponseType =
  | "OFFER_AVAILABLE"
  | "CLARIFICATION_REQUIRED"
  | "NO_INVENTORY"
  | "BUDGET_TOO_LOW"
  | "POLICY_REJECTED"
  | "NO_FEASIBLE_OFFER";

export interface MerchantResponse {
  response_type: MerchantResponseType;
  message: string;
  inventory_available: boolean;
  requested_budget_paise: number;
  catalog_total_paise?: number | null;
  closest_offer_price_paise?: number | null;
  budget_gap_paise: number;
  discount_attempted: boolean;
  policy_reasons: string[];
  suggested_actions: string[];
  language_provider?: string;
  language_model?: string | null;
}

export interface AgentMessage {
  id: number;
  transaction_id: string;
  sender: "BUYER_AGENT" | "MERCHANT_AGENT";
  recipient: "BUYER_AGENT" | "MERCHANT_AGENT";
  message_type: string;
  content: string;
  reason_code?: string | null;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface Deal {
  transaction_id: string;
  title: string;
  prompt: string;
  product_query: string;
  quantity: number;
  max_budget_paise: number;
  status: DealStatus;
  outcome_type?: string | null;
  recovered: boolean;
  rejection_reason?: string | null;
  merchant_response?: MerchantResponse | null;
  intelligence: Intelligence;
  initial_offer?: Offer | null;
  current_offer?: Offer | null;
  candidates: Candidate[];
  gate_results: GateResult[];
  events?: AuditEvent[];
  messages?: AgentMessage[];
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface ClarificationQuestion {
  field: "product_query" | "quantity" | "max_budget_paise";
  label: string;
  question: string;
  input_type: "text" | "number" | "money";
}

export interface ClarificationRequest {
  requires_clarification: true;
  original_prompt: string;
  known_fields: Partial<{
    product_query: string;
    quantity: number;
    max_budget_paise: number;
  }>;
  missing_fields: string[];
  questions: ClarificationQuestion[];
}

export interface Product {
  sku: string;
  name: string;
  brand?: string | null;
  model?: string | null;
  category: string;
  selling_price_paise: number;
  cost_price_paise: number;
  stock_quantity: number;
  margin_percent: number;
  is_overstock: boolean;
  is_active: boolean;
}

export interface MerchantPolicy {
  id: number;
  policy_name: string;
  min_margin_percent: number;
  max_discount_percent: number;
  allow_bundles: boolean;
  allow_substitutions: boolean;
  weight_margin: number;
  weight_revenue: number;
  weight_overstock: number;
  weight_discount_penalty: number;
  is_active: boolean;
  updated_at: string;
}

export interface Analytics {
  revenue_paise: number;
  deals_completed: number;
  sales_recovered: number;
  average_margin_percent: number;
  rejected_proposals: number;
  recovery_attempts: number;
  recovered_sales: number;
  recovery_rate_percent: number;
  revenue_recovered_paise: number;
  profit_recovered_paise: number;
  outcomes: { direct_match: number; recovered: number; lost: number };
}
