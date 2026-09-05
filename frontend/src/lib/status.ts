import { DealStatus } from "../types/commerce";

export const dealStatus: Record<DealStatus, { label: string; tone: "blue" | "amber" | "green" | "red" | "gray" }> = {
  WAITING_FOR_BUYER: { label: "Awaiting buyer approval", tone: "blue" },
  RECOVERING: { label: "Evaluating recovery options", tone: "amber" },
  RECOVERY_OFFER_SENT: { label: "Recovery proposal sent", tone: "blue" },
  COMPLETED: { label: "Deal completed", tone: "green" },
  LOST: { label: "Deal lost", tone: "red" },
};

export const eventLabels: Record<string, string> = {
  INTENT_RECEIVED: "Request created",
  INTENT_NORMALIZED: "Requirements structured",
  TRANSACTION_AT_RISK: "Recovery required",
  EVALUATION_START: "Policy evaluation started",
  CANDIDATE_APPROVED: "Proposal approved",
  CANDIDATE_REJECTED: "Proposal rejected by policy",
  PROPOSAL_SENT: "Proposal sent",
  MERCHANT_RESPONSE_SENT: "Merchant replied",
  PROPOSAL_REJECTED: "Buyer rejected proposal",
  RECOVERY_STARTED: "Recovery initiated",
  STRATEGIES_GENERATED: "Recovery strategies evaluated",
  STRATEGY_SELECTED: "Recovery strategy selected",
  RECOVERY_OFFER_SENT: "Recovery proposal sent",
  RECOVERY_DECLINED: "Recovery proposal declined",
  PURCHASE_APPROVED: "Purchase approved",
  DEAL_COMPLETED: "Deal completed",
};
