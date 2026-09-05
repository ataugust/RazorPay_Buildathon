"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, Bot, Check, ChevronRight, ClipboardList, History, Loader2, MessageCircle, PackageCheck, Search, Sparkles } from "lucide-react";
import { ClarificationRequest, Deal } from "../types/commerce";
import { dateTime, money, titleCase } from "../lib/format";
import { dealStatus, eventLabels } from "../lib/status";
import { Button, Card, Drawer, EmptyState, ErrorState, StatusBadge } from "./ui/DesignSystem";
import { DealTimeline } from "./DealTimeline";

const suggestions = [
  "Buy 5 HP monitors. Maximum total budget ₹70,000.",
  "Order 10 Lenovo IdeaPad laptops under ₹12 lakhs.",
  "Buy 20 Lenovo laptops with a maximum budget of ₹24 lakhs.",
];

const buyerEventMessages: Record<string, string> = {
  INTENT_RECEIVED: "Your purchase request was created.",
  INTENT_NORMALIZED: "The buyer agent organized your requirements for the merchant.",
  TRANSACTION_AT_RISK: "The original catalog match needs a better commercial option.",
  EVALUATION_START: "The merchant agent is checking inventory and preparing an offer.",
  CANDIDATE_APPROVED: "The merchant proposal passed the required commercial controls.",
  PROPOSAL_SENT: "The merchant agent sent a proposal for your review.",
  MERCHANT_RESPONSE_SENT: "The merchant agent explained why an eligible offer is not available.",
  PROPOSAL_REJECTED: "You declined the proposal. Your feedback was sent to the agents.",
  RECOVERY_STARTED: "The agents are evaluating a revised offer.",
  STRATEGIES_GENERATED: "Available alternatives were compared.",
  STRATEGY_SELECTED: "The best eligible alternative was selected.",
  RECOVERY_OFFER_SENT: "A revised merchant proposal is ready for your review.",
  RECOVERY_DECLINED: "The revised proposal was declined.",
  PURCHASE_APPROVED: "You approved the purchase.",
  DEAL_COMPLETED: "The purchase was completed and added to history.",
};

const buyerEventTypes = new Set(Object.keys(buyerEventMessages));

interface Props {
  deal: Deal | null;
  deals: Deal[];
  busy: boolean;
  error: string | null;
  onCreate: (prompt: string) => Promise<ClarificationRequest | null>;
  onReject: (reason?: string) => Promise<void>;
  onAccept: () => Promise<void>;
  onOpenDeal: (id: string) => Promise<void>;
  onReset: () => void;
}

export function BuyerWorkspace({ deal, deals, busy, error, onCreate, onReject, onAccept, onOpenDeal, onReset }: Props) {
  const [prompt, setPrompt] = useState(suggestions[0]);
  const [payloadOpen, setPayloadOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [clarification, setClarification] = useState<ClarificationRequest | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectionComment, setRejectionComment] = useState("");
  const [revisionMode, setRevisionMode] = useState<"budget" | "quantity" | "alternatives" | null>(null);
  const [revisionProduct, setRevisionProduct] = useState("");
  const [revisionQuantity, setRevisionQuantity] = useState("");
  const [revisionBudget, setRevisionBudget] = useState("");
  const [visibleEvents, setVisibleEvents] = useState(0);
  const [workingStep, setWorkingStep] = useState(0);
  const previousDeal = useRef<string | null>(null);

  const workingSteps = [
    "Buyer Agent is structuring your requirements",
    "Merchant Agent is checking matching inventory",
    "Control Plane is validating price and policy gates",
    "Merchant Agent is preparing a clear response",
  ];

  useEffect(() => {
    if (!busy) { setWorkingStep(0); return; }
    const timer = window.setInterval(
      () => setWorkingStep((step) => Math.min(step + 1, workingSteps.length - 1)),
      2400,
    );
    return () => window.clearInterval(timer);
  }, [busy, workingSteps.length]);

  const buyerEvents = (deal?.events || [])
    .filter((event) => buyerEventTypes.has(event.event_type))
    .map((event) => ({ ...event, message: buyerEventMessages[event.event_type] }));
  const eventCount = buyerEvents.length;
  const dealId = deal?.transaction_id;
  useEffect(() => {
    if (!dealId) return;
    if (previousDeal.current !== dealId) {
      previousDeal.current = dealId;
      setVisibleEvents(0);
      if (!eventCount) return;
      const firstTimer = window.setTimeout(() => setVisibleEvents(1), 250);
      return () => window.clearTimeout(firstTimer);
    }
    if (visibleEvents >= eventCount) return;
    const timer = window.setTimeout(
      () => setVisibleEvents((count) => Math.min(eventCount, count + 1)),
      visibleEvents === 0 ? 250 : 520,
    );
    return () => window.clearTimeout(timer);
  }, [dealId, eventCount, visibleEvents]);

  const submit = async () => {
    if (!prompt.trim()) return;
    setClarification(await onCreate(prompt.trim()));
  };

  const submitClarification = async () => {
    if (!clarification) return;
    const product = clarification.known_fields.product_query || answers.product_query;
    const quantity = clarification.known_fields.quantity || answers.quantity;
    const budget = clarification.known_fields.max_budget_paise
      ? clarification.known_fields.max_budget_paise / 100
      : answers.max_budget_paise?.replace(/[^\d.]/g, "");
    if (!product || !quantity || !budget) return;
    const expanded = `${clarification.original_prompt}. Product: ${product}. Quantity: ${quantity}. Maximum total budget Rs ${budget}.`;
    const next = await onCreate(expanded);
    setClarification(next);
  };

  if (!deal && showHistory) {
    return <PurchaseHistory deals={deals} busy={busy} onBack={() => setShowHistory(false)} onOpen={onOpenDeal} />;
  }

  if (!deal) {
    return (
      <main className="mx-auto flex min-h-[calc(100vh-65px)] w-full max-w-5xl items-center px-5 py-12 sm:px-8">
        <div className="mx-auto w-full max-w-3xl">
          <div className="mb-5 flex justify-end"><Button variant="secondary" onClick={() => setShowHistory(true)}><History className="h-4 w-4" /> Purchase history</Button></div>
          <div className="mb-8 text-center">
            <span className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm"><Sparkles className="h-5 w-5" /></span>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">What would you like to purchase?</h1>
            <p className="mt-3 text-base text-slate-500">Describe what you need and your budget. ASC will search inventory and prepare an authorized offer.</p>
          </div>
          <Card className="p-2 shadow-sm focus-within:border-indigo-300 focus-within:ring-4 focus-within:ring-indigo-50">
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={(event) => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submit(); }}
              rows={4}
              className="w-full resize-none rounded-lg border-0 bg-transparent p-4 text-lg leading-7 text-slate-900 outline-none placeholder:text-slate-400"
              placeholder="Buy 5 HP monitors. Maximum total budget ₹70,000."
            />
            <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2">
              <span className="hidden text-xs text-slate-400 sm:block">Ctrl + Enter to submit</span>
              <Button onClick={submit} loading={busy} className="ml-auto">Find the best offer <ChevronRight className="h-4 w-4" /></Button>
            </div>
          </Card>
          {busy && (
            <Card className="mt-5 overflow-hidden border-indigo-200 shadow-sm">
              <div className="flex items-center gap-3 border-b border-indigo-100 bg-indigo-50 px-5 py-4">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white"><Loader2 className="h-4 w-4 animate-spin" /></span>
                <div><p className="font-semibold text-slate-950">Your agents are working</p><p className="mt-0.5 text-xs text-indigo-700">Gemini Flash interprets language; ASC independently verifies every commercial decision.</p></div>
              </div>
              <div className="grid gap-2 p-4 sm:grid-cols-2">
                {workingSteps.map((step, index) => (
                  <div key={step} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${index === workingStep ? "bg-indigo-50 font-medium text-indigo-800" : index < workingStep ? "text-emerald-700" : "text-slate-400"}`}>
                    {index < workingStep ? <Check className="h-4 w-4" /> : index === workingStep ? <Loader2 className="h-4 w-4 animate-spin" /> : <span className="h-4 w-4 rounded-full border border-slate-300" />}
                    {step}
                  </div>
                ))}
              </div>
            </Card>
          )}
          {clarification && (
            <Card className="mt-5 border-indigo-200 p-5 shadow-sm">
              <div className="flex items-start gap-3"><span className="rounded-lg bg-indigo-50 p-2 text-indigo-600"><ClipboardList className="h-5 w-5" /></span><div><h2 className="font-semibold text-slate-950">A few details are needed</h2><p className="mt-1 text-sm text-slate-500">I understood {clarification.known_fields.product_query ? `the product (${clarification.known_fields.product_query})` : "part of your request"}, but I will not invent missing purchase constraints.</p></div></div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                {clarification.questions.map((question) => <label key={question.field} className={question.field === "product_query" ? "sm:col-span-2" : ""}><span className="mb-1.5 block text-sm font-medium text-slate-700">{question.question}</span><div className="relative">{question.input_type === "money" && <span className="absolute left-3 top-2.5 text-sm text-slate-500">₹</span>}<input type={question.input_type === "text" ? "text" : "number"} min={question.input_type === "text" ? undefined : 1} value={answers[question.field] || ""} onChange={(event) => setAnswers((current) => ({ ...current, [question.field]: event.target.value }))} placeholder={question.input_type === "money" ? "Maximum total budget" : question.label} className={`h-11 w-full rounded-lg border border-slate-300 bg-white pr-3 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 ${question.input_type === "money" ? "pl-7" : "pl-3"}`} /></div></label>)}
              </div>
              <div className="mt-5 flex justify-end"><Button onClick={submitClarification} loading={busy}>Continue request <ChevronRight className="h-4 w-4" /></Button></div>
            </Card>
          )}
          {error && <div className="mt-4"><ErrorState message={error} /></div>}
          <div className="mt-6 grid gap-2 sm:grid-cols-3">
            {suggestions.map((item) => <button key={item} onClick={() => setPrompt(item)} className="rounded-lg border border-slate-200 bg-white p-3 text-left text-sm leading-5 text-slate-600 transition hover:border-indigo-300 hover:text-indigo-700">{item}</button>)}
          </div>
          <div className="mt-8 flex items-center justify-center gap-2 text-sm text-slate-500"><Bot className="h-4 w-4 text-indigo-500" /><strong className="font-medium text-slate-700">ASC Buyer Assistant</strong><span>Finds → evaluates → compares → presents</span></div>
        </div>
      </main>
    );
  }

  const status = dealStatus[deal.status];
  const offer = deal.current_offer;
  const initial = deal.initial_offer;
  const isRecovery = deal.status === "RECOVERY_OFFER_SENT" || deal.recovered;
  const completed = deal.status === "COMPLETED";
  const savings = Math.max(0, (initial?.total_price_paise || 0) - (offer?.total_price_paise || 0));
  const unitBudget = Math.floor(deal.max_budget_paise / deal.quantity);
  const replaying = !completed && visibleEvents < eventCount;
  const visibleTimeline = buyerEvents.slice(0, visibleEvents);
  const nextEvent = buyerEvents[visibleEvents];
  const merchantReply = deal.merchant_response;

  const reviseRequest = (action: "budget" | "quantity" | "alternatives") => {
    const catalogTotal = merchantReply?.catalog_total_paise || merchantReply?.closest_offer_price_paise;
    const catalogUnit = merchantReply?.catalog_total_paise
      ? Math.floor(merchantReply.catalog_total_paise / deal.quantity)
      : Math.floor(deal.max_budget_paise / deal.quantity);
    setRevisionMode(action);
    setRevisionProduct(deal.product_query);
    setRevisionQuantity(String(action === "quantity" ? Math.max(1, Math.floor(deal.max_budget_paise / Math.max(1, catalogUnit))) : deal.quantity));
    setRevisionBudget(String(Math.floor((action === "budget" ? (catalogTotal || deal.max_budget_paise) : deal.max_budget_paise) / 100)));
  };

  const submitRevision = async () => {
    if (!revisionProduct.trim() || Number(revisionQuantity) < 1 || Number(revisionBudget) < 1) return;
    const alternatives = revisionMode === "alternatives" ? " Lower-cost product alternatives are allowed." : "";
    const revisedPrompt = `Product: ${revisionProduct.trim()}. Quantity: ${Number(revisionQuantity)}. Maximum total budget Rs ${Number(revisionBudget)}.${alternatives}`;
    const clarificationResult = await onCreate(revisedPrompt);
    if (!clarificationResult) setRevisionMode(null);
  };

  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8">
      <div className="mb-5 flex items-center justify-between"><button onClick={onReset} className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900"><ArrowLeft className="h-4 w-4" /> New purchase</button><button onClick={() => { onReset(); setShowHistory(true); }} className="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-800"><History className="h-4 w-4" /> Purchase history</button></div>
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div><h1 className="text-2xl font-semibold tracking-tight text-slate-950">{deal.title}</h1><p className="mt-1 text-sm text-slate-500">{deal.quantity} units · Maximum budget {money(deal.max_budget_paise)}</p></div>
        {replaying ? <StatusBadge tone="amber">Merchant agent working</StatusBadge> : <StatusBadge tone={status.tone}>{status.label}</StatusBadge>}
      </div>

      {completed ? (
        <Card className="overflow-hidden">
          <div className="border-b border-emerald-100 bg-emerald-50 px-6 py-8 text-center"><span className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-emerald-600 text-white"><Check className="h-5 w-5" /></span><h2 className="text-2xl font-semibold text-slate-950">Deal completed</h2><p className="mt-2 text-sm text-emerald-800">Negotiated autonomously. Authorized by you.</p></div>
          <div className="grid gap-6 p-6 sm:grid-cols-2 lg:grid-cols-4">
            <Summary label="Purchase" value={`${deal.quantity} × ${offer?.items?.[0]?.name || deal.product_query}`} />
            <Summary label="Original proposal" value={money(initial?.total_price_paise)} />
            <Summary label="Final price" value={money(offer?.total_price_paise)} strong />
            <Summary label="Buyer savings" value={money(savings)} />
          </div>
          <div className="border-t border-slate-100 px-6 py-4 text-xs text-slate-500">Transaction ID <span className="ml-2 font-mono text-slate-700">{deal.transaction_id}</span></div>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <div className="space-y-6">
            <Card className="p-5"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-950">Your request</h2><button onClick={() => setPayloadOpen(true)} className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-800"><ClipboardList className="h-4 w-4" /> View request details</button></div><p className="mt-3 rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-700">“{deal.prompt}”</p><dl className="mt-5 grid gap-4 sm:grid-cols-2"><Detail label="Product" value={deal.product_query} /><Detail label="Quantity" value={`${deal.quantity} units`} /><Detail label="Maximum budget" value={money(deal.max_budget_paise)} /><Detail label="Maximum / unit" value={money(unitBudget)} /></dl></Card>

            {deal.status === "LOST" && !replaying && merchantReply && <Card className="overflow-hidden border-amber-200"><div className="border-b border-amber-100 bg-amber-50 px-6 py-5"><div className="flex items-start gap-3"><span className="rounded-lg bg-white p-2 text-amber-700 shadow-sm"><MessageCircle className="h-5 w-5" /></span><div><p className="text-xs font-semibold uppercase tracking-wider text-amber-700">Reply from Merchant Agent</p><h2 className="mt-1 text-lg font-semibold text-slate-950">Unable to provide an eligible offer</h2></div></div></div><div className="p-6"><p className="text-sm leading-6 text-slate-700">{merchantReply.message}</p><div className="mt-5 grid gap-3 rounded-lg bg-slate-50 p-4 sm:grid-cols-3"><Detail label="Inventory" value={merchantReply.inventory_available ? "Available" : "Not available"} /><Detail label="Your budget" value={money(merchantReply.requested_budget_paise)} /><Detail label="Catalog total" value={money(merchantReply.catalog_total_paise)} />{merchantReply.closest_offer_price_paise ? <Detail label="Closest evaluated price" value={money(merchantReply.closest_offer_price_paise)} /> : null}{merchantReply.budget_gap_paise > 0 ? <Detail label="Budget difference" value={money(merchantReply.budget_gap_paise)} /> : null}<Detail label="Discount evaluated" value={merchantReply.discount_attempted ? "Yes" : "No"} /></div>{merchantReply.policy_reasons.length > 0 && <div className="mt-4 rounded-lg border border-amber-100 bg-amber-50/60 p-4"><p className="flex items-center gap-2 text-sm font-semibold text-amber-900"><AlertTriangle className="h-4 w-4" /> Why the offer was declined</p><ul className="mt-2 space-y-1 text-sm leading-5 text-amber-900/80">{merchantReply.policy_reasons.map((reason) => <li key={reason}>• {reason}</li>)}</ul></div>}<div className="mt-6"><p className="mb-3 text-sm font-medium text-slate-800">Modify and try again</p><div className="flex flex-wrap gap-2"><Button variant="secondary" onClick={() => reviseRequest("budget")}>Increase budget</Button><Button variant="secondary" onClick={() => reviseRequest("quantity")}>Reduce quantity</Button><Button onClick={() => reviseRequest("alternatives")}>Allow alternatives</Button></div>{revisionMode && <div className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4"><div className="mb-4"><h3 className="font-semibold text-slate-950">Revise this request</h3><p className="mt-1 text-sm text-slate-500">Edit the values here. You will stay in the deal workspace while the agents evaluate the revision.</p></div><div className="grid gap-3 sm:grid-cols-3"><label><span className="mb-1 block text-xs font-medium text-slate-600">Product</span><input value={revisionProduct} onChange={(event) => setRevisionProduct(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-indigo-500" /></label><label><span className="mb-1 block text-xs font-medium text-slate-600">Quantity</span><input type="number" min="1" value={revisionQuantity} onChange={(event) => setRevisionQuantity(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-indigo-500" /></label><label><span className="mb-1 block text-xs font-medium text-slate-600">Maximum budget (₹)</span><input type="number" min="1" value={revisionBudget} onChange={(event) => setRevisionBudget(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-indigo-500" /></label></div>{revisionMode === "alternatives" && <p className="mt-3 text-xs text-indigo-700">The revised request will explicitly authorize lower-cost product alternatives.</p>}<div className="mt-4 flex justify-end gap-2"><Button variant="ghost" onClick={() => setRevisionMode(null)}>Cancel</Button><Button onClick={submitRevision} loading={busy}>Send revised request</Button></div></div>}</div></div></Card>}

            {deal.messages && deal.messages.length > 0 && !replaying && <Card className="p-5"><div className="mb-4 flex items-center gap-2"><Bot className="h-4 w-4 text-indigo-600" /><h2 className="font-semibold text-slate-950">Agent conversation</h2></div><div className="space-y-3">{deal.messages.map((message) => <div key={message.id} className={`max-w-[88%] rounded-xl px-4 py-3 text-sm leading-5 ${message.sender === "BUYER_AGENT" ? "bg-slate-100 text-slate-700" : "ml-auto bg-indigo-50 text-indigo-950"}`}><p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{message.sender === "BUYER_AGENT" ? "Buyer Agent → Merchant Agent" : "Merchant Agent → Buyer Agent"}</p>{message.content}</div>)}</div></Card>}

            {replaying && <Card className="border-indigo-200 p-6 shadow-sm"><div className="flex items-start gap-4"><span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600"><Loader2 className="h-5 w-5 animate-spin" /><span className="absolute inset-0 animate-ping rounded-full border border-indigo-200" /></span><div><p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">{deal.rejection_reason ? "Feedback received" : "Deal created"}</p><h2 className="mt-1 text-lg font-semibold text-slate-950">{deal.rejection_reason ? "Evaluating a revised proposal" : "Waiting for the Merchant Agent"}</h2><p className="mt-1 text-sm text-slate-500">{nextEvent ? `Now working on: ${eventLabels[nextEvent.event_type] || titleCase(nextEvent.event_type)}` : "Preparing your proposal…"}</p></div></div></Card>}

            {deal.status === "RECOVERING" && <Card className="p-6"><div className="flex items-center gap-3"><span className="rounded-lg bg-amber-50 p-2 text-amber-700"><Search className="h-5 w-5 animate-pulse" /></span><div><h2 className="font-semibold text-slate-950">Offer declined</h2><p className="text-sm text-slate-500">ASC is checking merchant constraints and generating recovery strategies…</p></div></div></Card>}

            {offer && !replaying && <Card className="overflow-hidden"><div className={`border-b px-6 py-4 ${isRecovery ? "border-indigo-100 bg-indigo-50" : "border-slate-100 bg-slate-50"}`}><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">{isRecovery ? "Revised merchant proposal" : "Merchant proposal"}</p><h2 className="mt-1 text-lg font-semibold text-slate-950">{offer.items[0]?.name}</h2></div><StatusBadge tone={isRecovery ? "blue" : "green"}>{isRecovery ? "Revised offer" : "Ready to review"}</StatusBadge></div></div><div className="p-6"><div className="grid gap-5 sm:grid-cols-3"><Summary label="Quantity" value={`${deal.quantity}`} /><Summary label="Price / unit" value={money(Math.floor(offer.total_price_paise / deal.quantity))} /><Summary label="Total" value={money(offer.total_price_paise)} strong /></div>{isRecovery && <div className="mt-5 grid gap-3 rounded-lg border border-indigo-100 bg-indigo-50/60 p-4 sm:grid-cols-3"><Detail label="Original offer" value={money(initial?.total_price_paise)} /><Detail label="New offer" value={money(offer.total_price_paise)} /><Detail label="You save" value={money(savings)} /></div>}<ul className="mt-5 grid gap-2 text-sm text-slate-600 sm:grid-cols-2"><CheckItem text="Requested quantity" /><CheckItem text="Within your maximum budget" /><CheckItem text="Available from the merchant" /><CheckItem text="Ready for your decision" /></ul><div className="mt-6 flex justify-end gap-3"><Button variant="secondary" onClick={() => setRejectOpen(true)} disabled={busy}>{isRecovery ? "Decline" : "Reject offer"}</Button><Button onClick={onAccept} loading={busy}>Buy {money(offer.total_price_paise)}</Button></div></div></Card>}
            {error && <ErrorState message={error} />}
          </div>
          <Card className="h-fit p-5"><div className="mb-5 flex items-center gap-2"><PackageCheck className="h-4 w-4 text-indigo-600" /><h2 className="font-semibold text-slate-950">Deal progress</h2></div><DealTimeline events={visibleTimeline} compact />{replaying && <div className="ml-2 flex items-center gap-3 border-l border-slate-200 py-2 pl-5 text-sm text-indigo-700"><Loader2 className="h-4 w-4 animate-spin" /><span>{nextEvent ? `Working on ${eventLabels[nextEvent.event_type] || titleCase(nextEvent.event_type)}…` : "Preparing proposal…"}</span></div>}<div className="mt-5 border-t border-slate-100 pt-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Agent execution</p><AgentExecution label="Buyer Agent" provider={deal.intelligence.provider} model={deal.intelligence.model} /><AgentExecution label="Merchant Agent" provider={merchantReply?.language_provider} model={merchantReply?.language_model} /></div></Card>
        </div>
      )}

      <Drawer open={payloadOpen} title="Request details" onClose={() => setPayloadOpen(false)}><p className="mb-5 text-sm text-slate-500">These are the requirements the buyer agent sent to the merchant. Internal strategy and policy data stay in the Merchant Console.</p><Card className="p-5"><dl className="grid gap-5 sm:grid-cols-2"><Detail label="Product" value={deal.product_query} /><Detail label="Quantity" value={`${deal.quantity} units`} /><Detail label="Maximum total budget" value={money(deal.max_budget_paise)} /><Detail label="Maximum per unit" value={money(unitBudget)} />{deal.intelligence.max_delivery_days ? <Detail label="Delivery required within" value={`${deal.intelligence.max_delivery_days} days`} /> : null}</dl>{Object.values(deal.intelligence.hard_specs || {}).some(Boolean) && <div className="mt-5 border-t border-slate-100 pt-5"><p className="text-xs font-medium uppercase tracking-wide text-slate-400">Required specifications</p><ul className="mt-2 space-y-2 text-sm text-slate-700">{Object.entries(deal.intelligence.hard_specs).filter(([, value]) => value != null).map(([key, value]) => <li key={key}><span className="font-medium">{titleCase(key)}:</span> {String(value)}</li>)}</ul></div>}</Card></Drawer>
      <Drawer open={rejectOpen} title="Decline this offer" onClose={() => setRejectOpen(false)}><p className="text-sm leading-6 text-slate-600">You can optionally tell the buyer agent why this offer does not work. Your feedback helps it request a cheaper option, a different product, or another relevant alternative.</p><label className="mt-5 block"><span className="mb-2 block text-sm font-medium text-slate-800">Reason for declining <span className="font-normal text-slate-400">(optional)</span></span><textarea value={rejectionComment} onChange={(event) => setRejectionComment(event.target.value)} rows={5} maxLength={1000} placeholder="For example: The price is too high, please find a cheaper alternative." className="w-full resize-none rounded-lg border border-slate-300 p-3 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" /></label><div className="mt-6 flex justify-end gap-3"><Button variant="secondary" onClick={() => setRejectOpen(false)}>Cancel</Button><Button variant="danger" loading={busy} onClick={async () => { await onReject(rejectionComment.trim() || undefined); setRejectOpen(false); setRejectionComment(""); }}>Decline and evaluate alternatives</Button></div></Drawer>
    </main>
  );
}

function Detail({ label, value }: { label: string; value: string }) { return <div><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</dt><dd className="mt-1 text-sm font-medium text-slate-900">{value}</dd></div>; }
function Summary({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) { return <div><p className="text-xs font-medium text-slate-500">{label}</p><p className={`mt-1 ${strong ? "text-xl font-semibold text-indigo-700" : "text-base font-semibold text-slate-900"}`}>{value}</p></div>; }
function CheckItem({ text }: { text: string }) { return <li className="flex items-center gap-2"><span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-50"><Check className="h-3 w-3 text-emerald-600" /></span>{text}</li>; }
function AgentExecution({ label, provider, model }: { label: string; provider?: string | null; model?: string | null }) {
  const gemini = provider === "gemini";
  return <div className="mt-2 flex items-center justify-between gap-3 text-xs"><span className="font-medium text-slate-600">{label}</span><span className={`rounded-full px-2.5 py-1 font-medium ${gemini ? "bg-indigo-50 text-indigo-700" : "bg-amber-50 text-amber-700"}`}>{gemini ? model || "Gemini Flash" : "Safe deterministic fallback"}</span></div>;
}

function PurchaseHistory({ deals, busy, onBack, onOpen }: { deals: Deal[]; busy: boolean; onBack: () => void; onOpen: (id: string) => Promise<void> }) {
  const purchases = deals.filter((item) => item.status === "COMPLETED");
  return (
    <main className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8">
      <button onClick={onBack} className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900"><ArrowLeft className="h-4 w-4" /> Back to new purchase</button>
      <div className="mb-7"><h1 className="text-2xl font-semibold tracking-tight text-slate-950">Purchase history</h1><p className="mt-1 text-sm text-slate-500">Completed purchases authorized through your Buyer Workspace.</p></div>
      {!purchases.length ? <Card><EmptyState title="No completed purchases yet" description="A purchase will appear here after you approve a merchant proposal." /></Card> : <div className="space-y-3">{purchases.map((item) => {
        const purchasedOffer = item.current_offer || item.initial_offer;
        return <button key={item.transaction_id} disabled={busy} onClick={() => onOpen(item.transaction_id)} className="grid w-full gap-4 rounded-xl border border-slate-200 bg-white p-5 text-left transition hover:border-indigo-300 hover:shadow-sm disabled:opacity-60 sm:grid-cols-[1fr_auto_auto] sm:items-center"><div><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-slate-950">{purchasedOffer?.items?.[0]?.name || item.product_query}</h2><StatusBadge tone={item.recovered ? "blue" : "green"}>{item.recovered ? "Recovered deal" : "Direct purchase"}</StatusBadge></div><p className="mt-1 text-sm text-slate-500">{item.quantity} units · {dateTime(item.completed_at || item.updated_at)}</p><p className="mt-2 font-mono text-xs text-slate-400">{item.transaction_id}</p></div><div className="sm:text-right"><p className="text-xs font-medium uppercase tracking-wide text-slate-400">Final price</p><p className="mt-1 text-lg font-semibold text-slate-950">{money(purchasedOffer?.total_price_paise)}</p></div><ChevronRight className="hidden h-5 w-5 text-slate-400 sm:block" /></button>;
      })}</div>}
    </main>
  );
}
