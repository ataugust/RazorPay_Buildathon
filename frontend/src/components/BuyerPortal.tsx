"use client";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Bot, Check, CreditCard, History, Loader2, Package, Send, ShoppingBag, Sparkles } from "lucide-react";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { Button, Card, ErrorState } from "./ui/DesignSystem";

type Requirements = { product_query: string | null; quantity: number | null; budget_mode: "specified" | "no_limit" | "not_provided"; max_budget_paise: number | null; hard_specs: Record<string, string | number | null>; preferences: string[]; max_delivery_days: number | null; requested_discount_percent: number | null };
type Proposal = {offer_id: string; total_price_paise: number; requires_budget_approval?: boolean; original_budget_paise?: number; proposed_budget_paise?: number; value_included_paise?: number; items: {sku: string; name: string; quantity: number; unit_price_rupees: number; specifications: Record<string, string | number>}[]};
type Purchase = {id: string; prompt: string; state: string; requirements: Requirements; missing_fields: string[]; events: {state: string; label: string; timestamp: string}[]; reply: string | null; error: string | null; offer: Proposal | null};
type Checkout = {key_id: string; order_id: string; amount: number; currency: string; name: string; description: string; demo?: boolean};
type RazorpayResult = {razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string};
type RazorpayInstance = {open: () => void; on: (event: string, callback: (response: unknown) => void) => void};
declare global { interface Window { Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance } }
const inFlight = (state?: string) => ["PREPARING", "SENT", "WAITING", "NEGOTIATING"].includes(state || "");
const money = (amount: number | null) => amount === null ? "No budget limit" : new Intl.NumberFormat("en-IN", {style:"currency", currency:"INR", maximumFractionDigits:0}).format(amount / 100);
async function call<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(`/backend-api/api/buyer${path}`, {method, credentials:"same-origin", headers:{"Content-Type":"application/json"}, body: body === undefined ? undefined : JSON.stringify(body), cache:"no-store"});
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : "The request could not be completed. Please try again.");
  return data;
}

async function loadRazorpayCheckout() {
  if (window.Razorpay) return true;
  return new Promise<boolean>((resolve) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-asc-razorpay="checkout"]');
    if (existing) { existing.addEventListener("load", () => resolve(Boolean(window.Razorpay)), {once:true}); existing.addEventListener("error", () => resolve(false), {once:true}); return; }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.dataset.ascRazorpay = "checkout";
    script.onload = () => resolve(Boolean(window.Razorpay));
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export function BuyerPortal() {
  const [ready, setReady] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [purchase, setPurchase] = useState<Purchase | null>(null);
  const [history, setHistory] = useState<Purchase[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [declining, setDeclining] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [demoPayment, setDemoPayment] = useState<string | null>(null);
  const [form, setForm] = useState<Requirements | null>(null);
  const active = useRef<string | null>(null);
  const mounted = useRef(true);
  const adopt = (next: Purchase) => {active.current = next.id; setPurchase(next); localStorage.setItem("asc-active-request", next.id);};
  useEffect(() => {
    mounted.current = true;
    call("/session", "POST").then(async () => {
      if (!mounted.current) return;
      setReady(true);
      const saved = localStorage.getItem("asc-active-request");
      if (saved) {
        try { const found = await call<Purchase>(`/requests/${saved}`); if (mounted.current) adopt(found); }
        catch { localStorage.removeItem("asc-active-request"); }
      }
    }).catch((e) => setError(e.message));
    return () => { mounted.current = false; };
  }, []);
  const purchaseId = purchase?.id, purchaseState = purchase?.state;
  useEffect(() => {
    if (!purchaseId || !inFlight(purchaseState)) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try { const next = await call<Purchase>(`/requests/${purchaseId}`); if (!cancelled && active.current === next.id) setPurchase(next); }
      catch (e) { if (!cancelled) setError((e as Error).message); }
      if (!cancelled) timer = setTimeout(poll, 900);
    };
    timer = setTimeout(poll, 500);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [purchaseId, purchaseState]);
  useEffect(() => {if (purchase?.state === "NEEDS_DETAILS") setForm(purchase.requirements);}, [purchase]);
  const run = async (action: () => Promise<Purchase>) => {
    if (busy) return;
    setBusy(true); setError(null);
    try { adopt(await action()); setEditing(false); setDeclining(false); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const submit = () => {if (prompt.trim() && ready) run(() => call<Purchase>("/requests", "POST", {prompt:prompt.trim()}));};
  const reset = () => {active.current = null; localStorage.removeItem("asc-active-request"); setPurchase(null); setShowHistory(false); setError(null); setEditing(false); setDeclining(false);};
  const openHistory = async () => {
    setError(null);
    try { const result = await call<{requests:Purchase[]}>("/requests"); setHistory(result.requests.reverse()); setShowHistory(true); }
    catch (e) { setError((e as Error).message); }
  };
  const revise = () => {if (purchase) {setForm(purchase.requirements); setEditing(true);}};
  const save = () => {
    if (!purchase || !form || !form.product_query?.trim() || !form.quantity || form.budget_mode === "not_provided" || (form.budget_mode === "specified" && !form.max_budget_paise)) return;
    run(() => call(`/requests/${purchase.id}`, "PATCH", {requirements:form}));
  };
  const startCheckout = async () => {
    if (!purchase || busy) return;
    setBusy(true); setError(null);
    try {
      const result = await call<{purchase: Purchase; checkout: Checkout}>(`/requests/${purchase.id}/checkout`, "POST");
      adopt(result.purchase);
      if (result.checkout.demo) {
        setDemoPayment("Opening secure checkout");
        await new Promise(resolve => setTimeout(resolve, 500));
        setDemoPayment("Processing payment securely");
        await new Promise(resolve => setTimeout(resolve, 900));
        adopt(await call<Purchase>(`/requests/${purchase.id}/payment/demo`, "POST"));
        setDemoPayment("Payment successful · Secured with Razorpay");
        await new Promise(resolve => setTimeout(resolve, 700));
        setDemoPayment(null);
        return;
      }
      if (!await loadRazorpayCheckout() || !window.Razorpay) throw new Error("Razorpay Checkout could not load. Check your connection and try again.");
      let paymentSubmitted = false;
      const checkout = new window.Razorpay({
        key: result.checkout.key_id, amount: result.checkout.amount, currency: result.checkout.currency,
        name: result.checkout.name, description: result.checkout.description, order_id: result.checkout.order_id,
        theme: {color: "#4f46e5"},
        handler: async (payment: RazorpayResult) => {
          paymentSubmitted = true; setBusy(true); setError(null);
          try { adopt(await call<Purchase>(`/requests/${purchase.id}/payment/verify`, "POST", payment)); }
          catch (e) { setError((e as Error).message); }
          finally { setBusy(false); }
        },
        modal: {ondismiss: async () => {
          if (paymentSubmitted) return;
          try { adopt(await call<Purchase>(`/requests/${purchase.id}/payment/cancel`, "POST")); }
          catch (e) { setError((e as Error).message); }
        }},
      });
      checkout.on("payment.failed", () => setError("Razorpay could not complete the payment. No purchase was fulfilled; you can try again."));
      checkout.open();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const waiting = inFlight(purchase?.state), needDetails = purchase?.state === "NEEDS_DETAILS";
  const fields = needDetails ? purchase.missing_fields : ["product_query", "quantity", "budget", "specifications", "discount"];
  const editable = form && (needDetails || editing);

  return <div className="min-h-screen bg-slate-50 text-slate-900"><WorkspaceHeader workspace="buyer" online={ready} />
    {demoPayment && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-5 backdrop-blur-sm"><Card className="w-full max-w-sm p-8 text-center shadow-2xl"><div className={`mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full ${demoPayment.startsWith("Payment successful") ? "bg-emerald-100 text-emerald-600" : "bg-indigo-100 text-indigo-600"}`}>{demoPayment.startsWith("Payment successful") ? <Check className="h-7 w-7"/> : <Loader2 className="h-7 w-7 animate-spin"/>}</div><h2 className="text-xl font-semibold">{demoPayment}</h2><p className="mt-2 text-sm text-slate-500">Razorpay secure checkout · Demo mode</p>{!demoPayment.startsWith("Payment successful") && <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full w-2/3 animate-pulse rounded-full bg-indigo-600"/></div>}</Card></div>}
    <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
      <div className="mb-7 flex items-center justify-between"><button onClick={reset} className="flex items-center gap-2 text-sm text-slate-500"><ArrowLeft className="h-4 w-4" /> New purchase</button><button onClick={openHistory} className="flex items-center gap-2 text-sm text-indigo-600"><History className="h-4 w-4" /> Purchase history</button></div>
      {error && <div className="mb-5" role="alert"><ErrorState message={error} /></div>}
      {showHistory ? <div><h1 className="mb-2 text-2xl font-semibold">Your purchases and requests</h1><p className="mb-6 text-sm text-slate-500">Open a request to view the merchant reply or continue where you left off.</p>{!history.length && <Card className="p-8 text-center text-slate-500">No requests yet.</Card>}<div className="space-y-3">{history.map(item => <button key={item.id} onClick={() => {adopt(item); setShowHistory(false);}} className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white p-5 text-left"><div><p className="font-semibold">{item.requirements.product_query || item.prompt}</p><p className="mt-1 text-sm text-slate-500">{item.state === "COMPLETED" ? "Payment complete" : item.state === "PAYMENT_PENDING" ? "Payment pending" : item.state === "REPLIED" ? "Merchant replied" : item.state === "NEEDS_DETAILS" ? "Needs your details" : "Request saved"}</p></div><ArrowRight className="h-4 w-4" /></button>)}</div></div> : !purchase ?
      <div className="mx-auto max-w-3xl py-12 sm:py-20"><div className="mb-8 text-center"><span className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-white"><ShoppingBag className="h-6 w-6" /></span><h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">What would you like to buy?</h1><p className="mt-3 text-slate-500">Tell your buyer assistant what you need. We’ll bring the merchant’s proposal to you.</p></div><Card className="p-3 shadow-sm"><textarea aria-label="Purchase request" value={prompt} onChange={e=>setPrompt(e.target.value)} onKeyDown={e=>{if(e.key==="Enter" && (e.ctrlKey || e.metaKey)) submit();}} placeholder="Buy me 2 laptops, max budget 1 lakh rupees" rows={4} className="w-full resize-none bg-transparent p-3 text-lg outline-none" /><div className="flex justify-end border-t border-slate-100 pt-3"><Button loading={busy} disabled={!ready || !prompt.trim()} onClick={submit}>Send request <Send className="h-4 w-4" /></Button></div></Card><div className="mt-4 flex flex-wrap gap-2">{["Buy me 2 laptops max budget 1 lakh rupees", "Buy 5 laptops with Ryzen 5 and 8 GB RAM", "Buy any laptop, no budget limit"].map(text=><button key={text} onClick={()=>setPrompt(text)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs text-slate-600">{text}</button>)}</div></div> :
      <div className="grid gap-6 lg:grid-cols-[1fr_300px]"><div className="space-y-5"><div><h1 className="text-2xl font-semibold">{purchase.requirements.product_query || "Your purchase request"}</h1><p className="mt-2 text-sm text-slate-500">{purchase.requirements.quantity ? `${purchase.requirements.quantity} units · ` : ""}{purchase.requirements.budget_mode === "not_provided" ? "Budget not specified" : money(purchase.requirements.max_budget_paise)}</p></div>
        <Card className="p-5"><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Your request</p><p className="mt-3 leading-7">{purchase.prompt}</p><div className="mt-3 flex flex-wrap gap-2">{purchase.requirements.requested_discount_percent !== null && <span className="rounded-lg bg-slate-100 px-3 py-1 text-sm">{purchase.requirements.requested_discount_percent}% discount requested</span>}{Object.entries(purchase.requirements.hard_specs).filter(([,v])=>v!==null).map(([key,value])=><span key={key} className="rounded-lg bg-slate-100 px-3 py-1 text-sm">{key === "min_ram_gb" ? `${value} GB RAM` : key === "min_storage_gb" ? `${value} GB storage` : value}</span>)}</div></Card>
        {waiting && <Card className="overflow-hidden border-indigo-100"><div className="flex items-center gap-4 bg-indigo-50 p-6"><div className="rounded-2xl bg-white p-3 text-indigo-600 motion-safe:animate-pulse"><Send className="h-6 w-6" /></div><div role="status" aria-live="polite"><h2 className="font-semibold">{purchase.state === "NEGOTIATING" ? (purchase.events.at(-1)?.label || "Negotiating with the merchant") : purchase.state === "PREPARING" ? "Preparing your request" : "Waiting for the merchant"}</h2><p className="mt-1 text-sm text-slate-600">{purchase.state === "NEGOTIATING" ? "Your buyer assistant is comparing the merchant’s revised terms and included value." : purchase.state === "PREPARING" ? "Your requirements are being added to the request." : "Your request has been sent. The reply will appear here."}</p></div><Loader2 className="ml-auto h-5 w-5 animate-spin text-indigo-500" /></div></Card>}
        {editable && <Card className="p-6"><h2 className="font-semibold">{needDetails ? "A few details are needed" : "Revise your request"}</h2><p className="mt-1 text-sm text-slate-500">{needDetails ? "We’ll keep everything you have already provided." : "Update the requirements here and send them to the merchant."}</p><div className="mt-5 space-y-4">
          {fields.includes("product_query") && <Field label="What product would you like?" value={form.product_query || ""} onChange={v=>setForm({...form,product_query:v})} />}
          {fields.includes("quantity") && <Field label="How many units do you need?" type="number" value={form.quantity?.toString() || ""} onChange={v=>setForm({...form,quantity:v ? Number(v) : null})} />}
          {fields.includes("budget") && <div><label className="mb-2 block text-sm font-medium">Budget preference</label><select aria-label="Budget preference" value={form.budget_mode} onChange={e=>setForm({...form,budget_mode:e.target.value as Requirements["budget_mode"],max_budget_paise:null})} className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3"><option value="not_provided">Choose a budget preference</option><option value="specified">Set a maximum total budget</option><option value="no_limit">No budget limit — show me offers</option></select>{form.budget_mode === "specified" && <div className="mt-3"><Field label="Maximum total budget (₹)" type="number" value={form.max_budget_paise ? String(form.max_budget_paise/100) : ""} onChange={v=>setForm({...form,max_budget_paise:v ? Math.round(Number(v)*100) : null})} /></div>}</div>}
          {fields.includes("specifications") && <div className="grid gap-3 sm:grid-cols-3"><Field label="Minimum RAM (GB)" type="number" value={String(form.hard_specs.min_ram_gb || "")} onChange={v=>setForm({...form,hard_specs:{...form.hard_specs,min_ram_gb:v ? Number(v):null}})} /><Field label="Processor family / tier" value={String(form.hard_specs.min_cpu_tier || "")} onChange={v=>setForm({...form,hard_specs:{...form.hard_specs,min_cpu_tier:v || null}})} /><Field label="Minimum storage (GB)" type="number" value={String(form.hard_specs.min_storage_gb || "")} onChange={v=>setForm({...form,hard_specs:{...form.hard_specs,min_storage_gb:v ? Number(v):null}})} /></div>}
          {fields.includes("discount") && <Field label="Requested discount (%) — optional" type="number" value={String(form.requested_discount_percent ?? "")} onChange={v=>setForm({...form,requested_discount_percent:v ? Number(v):null})} />}
        </div><div className="mt-5 flex justify-end gap-2">{editing && <Button variant="ghost" onClick={()=>setEditing(false)}>Cancel</Button>}<Button loading={busy} onClick={save} disabled={!form.product_query || !form.quantity || form.quantity < 1 || form.budget_mode === "not_provided" || (form.budget_mode === "specified" && !form.max_budget_paise)}>Send to merchant <ArrowRight className="h-4 w-4" /></Button></div></Card>}
        {purchase.state === "ERROR" && <Card className="p-5"><ErrorState message={purchase.error || "The request was interrupted."}/><Button onClick={revise} className="mt-3">Review and retry</Button></Card>}
        {!waiting && purchase.reply && <Card className="overflow-hidden"><div className="flex items-center gap-3 border-b border-slate-100 bg-white px-6 py-4"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-indigo-700"><Bot className="h-5 w-5"/></span><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">Merchant agent</p><h2 className="font-semibold">Reply from merchant</h2></div></div><div className="p-6"><p className="text-sm leading-7 text-slate-700">{purchase.reply}</p>{purchase.offer && <div className="mt-5 space-y-4">{purchase.offer.requires_budget_approval && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><p className="font-semibold text-amber-900">Revised budget approval required</p><p className="mt-1 text-sm text-amber-800">Original budget {money(purchase.offer.original_budget_paise ?? 0)} · Negotiated total {money(purchase.offer.proposed_budget_paise ?? purchase.offer.total_price_paise)} · Included value {money(purchase.offer.value_included_paise ?? 0)}</p></div>}{purchase.offer.items.map(item=><div key={item.sku} className="rounded-xl bg-slate-50 p-4"><p className="font-semibold">{item.quantity} × {item.name}</p><p className="mt-1 text-sm text-slate-500">{item.unit_price_rupees === 0 ? "Included at no charge" : `${money(item.unit_price_rupees*100)} per unit`}</p><div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">{Object.entries(item.specifications).map(([k,v])=><span key={k}>{k === "ram_gb" ? `${v} GB RAM` : k === "storage_gb" ? `${v} GB storage` : v}</span>)}</div></div>)}<div className="flex items-center justify-between"><span className="font-medium">Total</span><strong className="text-2xl text-indigo-600">{money(purchase.offer.total_price_paise)}</strong></div></div>}
        {(purchase.state === "REPLIED" || purchase.state === "PAYMENT_PENDING") && !editing && <div className="mt-6 flex flex-wrap justify-end gap-3">{purchase.state === "REPLIED" && <Button variant="secondary" onClick={revise}>Request changes</Button>}{purchase.state === "REPLIED" && !purchase.offer && <Button loading={busy} onClick={()=>run(()=>call(`/requests/${purchase.id}/negotiate`,"POST"))}><Sparkles className="h-4 w-4"/> Negotiate</Button>}{purchase.offer && <>{purchase.state === "REPLIED" && <Button variant="ghost" onClick={()=>setDeclining(true)}>Decline</Button>}<Button loading={busy} onClick={startCheckout}><CreditCard className="h-4 w-4"/>{purchase.state === "PAYMENT_PENDING" ? "Resume Razorpay payment" : purchase.offer.requires_budget_approval ? `Accept ${money(purchase.offer.proposed_budget_paise ?? purchase.offer.total_price_paise)} · Pay with Razorpay` : `Pay ${money(purchase.offer.total_price_paise)} with Razorpay`}</Button></>}</div>}
        {declining && <div className="mt-4 rounded-xl bg-slate-50 p-4"><label className="text-sm font-medium">Why are you declining? (optional)</label><textarea aria-label="Reason for declining" value={feedback} onChange={e=>setFeedback(e.target.value)} maxLength={1000} className="mt-2 w-full rounded-lg border border-slate-200 p-3" rows={3}/><Button loading={busy} onClick={()=>run(()=>call(`/requests/${purchase.id}/decline`,"POST",{reason:feedback}))}>Send decision</Button></div>}
        {purchase.state === "PAYMENT_PENDING" && <p className="mt-5 flex items-center gap-2 text-indigo-700"><CreditCard className="h-5 w-5"/>Secure payment is pending.</p>}{purchase.state === "COMPLETED" && <p className="mt-5 flex items-center gap-2 text-emerald-700"><Check className="h-5 w-5"/>Payment successful · Secured with Razorpay. Your purchase is complete.</p>}{purchase.state === "DECLINED" && <div className="mt-5"><p className="mb-3 text-slate-500">You declined this offer.</p><Button variant="secondary" onClick={revise}>Revise request</Button></div>}</div></Card>}
      </div><aside><Card className="p-5"><div className="mb-6 flex items-center gap-2"><Package className="h-4 w-4 text-indigo-600"/><h2 className="font-semibold">Request progress</h2></div><ol className="space-y-5">{[{state:"PREPARING",label:"Preparing request"},{state:"SENT",label:"Request sent"},{state:"WAITING",label:"Waiting for response"},...(purchase.events.some(e=>e.state==="NEGOTIATING")?[{state:"NEGOTIATING",label:"Negotiating best terms"}]:[]),{state:"REPLIED",label:"Reply received"}].map(step=>{const cycleStart=purchase.events.map(e=>e.state).lastIndexOf("PREPARING"); const reached=purchase.events.slice(Math.max(0,cycleStart)).some(e=>e.state===step.state); const current=purchase.state===step.state; return <li key={step.state} className="flex items-center gap-3 text-sm"><span className={`flex h-7 w-7 items-center justify-center rounded-full ${reached ? "bg-indigo-50 text-indigo-600":"bg-slate-100 text-slate-300"}`}>{current && waiting ? <Loader2 className="h-4 w-4 animate-spin"/> : reached ? <Check className="h-4 w-4"/>:<span className="h-2 w-2 rounded-full bg-current"/>}</span><span className={reached ? "text-slate-800":"text-slate-400"}>{step.label}</span></li>;})}</ol>{needDetails && <p className="mt-5 text-sm text-indigo-700">Waiting for your details before sending.</p>}</Card></aside></div>}
    </main></div>;
}
function Field({label,value,onChange,type="text"}:{label:string;value:string;onChange:(value:string)=>void;type?:string}) {
  return <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">{label}</span><input value={value} type={type} min={type==="number" ? 1 : undefined} onChange={e=>onChange(e.target.value)} className="h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm outline-none focus:border-indigo-500"/></label>;
}
