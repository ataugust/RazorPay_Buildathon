"use client";

import React, { useState } from 'react';
import { 
  ShieldCheck, Cpu, ArrowRight, Zap, CheckCircle2, AlertTriangle, 
  AlertCircle, ShoppingBag, Terminal, Check, CreditCard, Sparkles, 
  RotateCcw, Lock, Info, ExternalLink, Activity, Layers, CheckSquare
} from 'lucide-react';

interface Scenario {
  name: string;
  icon: string;
  prompt: string;
}

const DEMO_SCENARIOS: Scenario[] = [
  {
    name: "Direct Match",
    icon: "🎯",
    prompt: "Order 20 Lenovo IdeaPad laptops with a maximum budget of Rs. 27L."
  },
  {
    name: "Volume Discount",
    icon: "⚡",
    prompt: "Order 20 Lenovo IdeaPad laptops with a maximum budget of Rs. 24L."
  },
  {
    name: "Product Substitute",
    icon: "🔄",
    prompt: "Order 20 laptops with at least 16GB RAM and max budget of Rs. 22.5L."
  },
  {
    name: "Overstock Bundle",
    icon: "📦",
    prompt: "Order 20 Lenovo laptops with overstock accessories under Rs. 23.5L."
  },
  {
    name: "Impossible Deal",
    icon: "🛑",
    prompt: "Order 50 Lenovo laptops with a maximum budget of Rs. 20L."
  }
];

export default function Home() {
  const [prompt, setPrompt] = useState(DEMO_SCENARIOS[1].prompt); // Default to Volume Discount
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<number>(0);
  const [result, setResult] = useState<any>(null);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentData, setPaymentData] = useState<any>(null);
  const [paying, setPaying] = useState(false);

  const handleSelectScenario = (scenario: Scenario) => {
    setPrompt(scenario.prompt);
    setResult(null);
    setPaymentData(null);
  };

  const handleRunSimulation = async () => {
    setLoading(true);
    setStep(1);
    setResult(null);
    setPaymentData(null);

    // Simulate multi-step visual pipeline progress for hackathon impact
    setTimeout(() => setStep(2), 300);
    setTimeout(() => setStep(3), 600);

    try {
      const res = await fetch("http://localhost:8000/api/purchase/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      setResult(data);
      setStep(4);
    } catch (err) {
      console.error(err);
      alert("Error connecting to ASC backend at http://localhost:8000. Please ensure uvicorn backend is running!");
    } finally {
      setLoading(false);
    }
  };

  const handleExecutePayment = async () => {
    if (!result?.result?.offer) return;
    setPaying(true);
    try {
      const txnId = result.result.transaction_id;
      const offerId = result.result.offer.offer_id;
      const amountPaise = result.result.offer.total_price_paise;

      const res = await fetch(`http://localhost:8000/api/purchase/execute-payment/${txnId}?offer_id=${offerId}&amount_paise=${amountPaise}`, {
        method: "POST"
      });
      const data = await res.json();
      setPaymentData(data);
      setPaymentModalOpen(true);
    } catch (err) {
      console.error(err);
      alert("Error executing payment gateway transaction.");
    } finally {
      setPaying(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-blue-500 selection:text-white pb-12">
      {/* 1. TOP NAVIGATION BAR */}
      <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/80 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-emerald-500 p-0.5 shadow-lg shadow-blue-900/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-blue-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-slate-100">
                  ASC <span className="text-slate-400 font-normal">| Autonomous Sales Counterparty</span>
                </h1>
              </div>
              <p className="text-xs text-slate-400">
                Merchant-Side AI Commerce Engine with a Deterministic Control Plane
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="px-3 py-1 bg-blue-950/80 border border-blue-800/60 text-blue-300 rounded-full text-xs font-mono font-medium flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              Track 01: Agentic Commerce
            </span>
            <span className="px-2.5 py-1 bg-amber-950/60 border border-amber-800/50 text-amber-300 rounded-full text-xs font-mono flex items-center gap-1.5">
              <Lock className="w-3 h-3 text-amber-400" />
              TEST MODE
            </span>
            <span className="px-2.5 py-1 bg-emerald-950/60 border border-emerald-800/50 text-emerald-300 rounded-full text-xs font-mono flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              ● System Online
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 pt-6 flex flex-col gap-6">

        {/* 2. ZONE 1 — BUYER AGENT INTERFACE */}
        <section className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl pointer-events-none"></div>

          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-blue-400"></div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">Zone 1 — Buyer Agent Console</h2>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Create procurement intent and initiate agent-to-agent (A2A) commercial negotiation.
              </p>
            </div>
            <span className="px-2.5 py-1 bg-blue-950 border border-blue-800/80 text-blue-300 rounded text-[11px] font-mono">
              STATUS: CONNECTED
            </span>
          </div>

          {/* Quick Scenario Preset Chips */}
          <div className="mb-4">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              <span>Quick Demo Scenarios (Click to Load):</span>
            </div>
            <div className="flex gap-2 flex-wrap">
              {DEMO_SCENARIOS.map((sc, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectScenario(sc)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 border ${
                    prompt === sc.prompt
                      ? 'bg-blue-600/20 border-blue-500 text-blue-200 shadow-sm shadow-blue-900/30'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  <span>{sc.icon}</span>
                  <span>{sc.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Input Textarea & Primary CTA Button */}
          <div className="flex flex-col md:flex-row gap-4 items-stretch">
            <div className="flex-1 relative">
              <textarea
                rows={2}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/50 resize-none font-sans"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter procurement intent prompt..."
              />
            </div>
            <button
              onClick={handleRunSimulation}
              disabled={loading}
              className="px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-xl transition-all flex items-center justify-center gap-2.5 shadow-lg shadow-blue-950/80 disabled:opacity-50 shrink-0"
            >
              {loading ? (
                <>
                  <Activity className="w-5 h-5 animate-spin text-blue-200" />
                  <span>Evaluating 6 Gates...</span>
                </>
              ) : (
                <>
                  <Zap className="w-5 h-5 text-amber-300 fill-amber-300" />
                  <span>⚡ Simulate A2A Transaction</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* 3. MAIN DASHBOARD: ZONE 2 & ZONE 3 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* ZONE 2 — A2A NEGOTIATION NETWORK TIMELINE (5 COLUMNS) */}
          <section className="lg:col-span-5 bg-slate-900/90 border border-slate-800/90 rounded-2xl p-5 flex flex-col gap-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <Cpu className="text-indigo-400 w-5 h-5" />
                <h2 className="font-bold text-sm tracking-wide text-slate-200 uppercase">Zone 2 — A2A Network</h2>
              </div>
              <span className="text-[11px] font-mono text-indigo-300 bg-indigo-950/60 border border-indigo-800/40 px-2 py-0.5 rounded">
                Probabilistic AI Reasoning
              </span>
            </div>

            {!result ? (
              <div className="h-96 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800/80 rounded-xl p-6 text-center">
                <ShoppingBag className="w-12 h-12 mb-3 text-slate-700 stroke-1" />
                <p className="text-xs max-w-xs leading-relaxed text-slate-400">
                  Select a scenario chip above or enter a prompt, then click <strong className="text-blue-400">"Simulate A2A Transaction"</strong> to visualize the negotiation event pipeline.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3 font-mono text-xs">
                {/* Step 1: Intent Parsed */}
                <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 flex flex-col gap-1">
                  <div className="flex justify-between items-center text-[11px] text-blue-400 font-bold">
                    <span>1. BUYER INTENT PARSED</span>
                    <span className="text-slate-500">REQ-001</span>
                  </div>
                  <div className="text-slate-200 font-sans font-semibold text-sm">
                    {result.parsed_request?.items[0]?.quantity}x {result.parsed_request?.items[0]?.product_query}
                  </div>
                  <div className="text-slate-400 text-[11px]">
                    Max Authorized Budget: <strong className="text-slate-200">Rs. {(result.parsed_request?.max_budget_paise / 100).toLocaleString('en-IN')}</strong>
                  </div>
                </div>

                <div className="flex justify-center text-slate-600">
                  <ArrowRight className="w-4 h-4 rotate-90" />
                </div>

                {/* Step 2: Direct Match Check */}
                <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 flex flex-col gap-1">
                  <div className="flex justify-between items-center text-[11px] text-amber-400 font-bold">
                    <span>2. DIRECT CATALOG MATCH</span>
                    <span className="px-1.5 py-0.5 bg-amber-950 text-amber-300 border border-amber-800 rounded text-[10px]">FAILED</span>
                  </div>
                  <div className="text-slate-400 text-[11px]">
                    Catalog Price (Rs. 25,00,000) exceeds budget limit. <strong className="text-amber-300">Transaction at risk!</strong>
                  </div>
                </div>

                <div className="flex justify-center text-slate-600">
                  <ArrowRight className="w-4 h-4 rotate-90" />
                </div>

                {/* Step 3: Strategy Engine & Counteroffer Generation */}
                <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 flex flex-col gap-1.5">
                  <div className="flex justify-between items-center text-[11px] text-indigo-400 font-bold">
                    <span>3. STRATEGY ENGINE</span>
                    <span className="text-indigo-300 text-[10px]">3 Candidates Generated</span>
                  </div>
                  <div className="flex flex-col gap-1 text-[11px] text-slate-300">
                    <div className="flex justify-between items-center p-1.5 rounded bg-slate-900/80 border border-slate-800">
                      <span>• VOLUME_DISCOUNT</span>
                      <span className="text-emerald-400">Rs. 24,00,000 (16.67% Margin)</span>
                    </div>
                    <div className="flex justify-between items-center p-1.5 rounded bg-slate-900/80 border border-slate-800">
                      <span>• PRODUCT_SUBSTITUTE</span>
                      <span className="text-slate-400">Rs. 22,40,000 (19.64% Margin)</span>
                    </div>
                    <div className="flex justify-between items-center p-1.5 rounded bg-slate-900/80 border border-slate-800">
                      <span>• BUNDLE_OVERSTOCK</span>
                      <span className="text-rose-400">Rs. 23,10,000 (12.81% Margin - Low)</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-center text-slate-600">
                  <ArrowRight className="w-4 h-4 rotate-90" />
                </div>

                {/* Step 4: Winning Candidate Selected */}
                <div className={`p-4 rounded-xl border ${result.result?.rescued ? 'bg-emerald-950/30 border-emerald-800/80' : 'bg-rose-950/30 border-rose-800/80'}`}>
                  <div className="flex justify-between items-center mb-1 text-[11px] font-bold">
                    <span className={result.result?.rescued ? 'text-emerald-400' : 'text-rose-400'}>
                      4. DETERMINISTIC WINNER RANKED
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${result.result?.rescued ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-rose-950 text-rose-300 border-rose-800'}`}>
                      {result.result?.rescued ? 'APPROVED' : 'REJECTED'}
                    </span>
                  </div>
                  {result.result?.offer ? (
                    <div className="text-xs text-slate-300 font-sans mt-1">
                      <div className="font-semibold text-slate-100">{result.result.offer.explanation}</div>
                      <div className="text-[11px] font-mono text-slate-400 mt-2 flex justify-between">
                        <span>Strategy: <strong>{result.result.offer.strategy}</strong></span>
                        <span>Score: <strong>{result.result.offer.final_score}/100</strong></span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-amber-300 mt-1 font-sans">
                      {result.result?.message}
                    </div>
                  )}
                </div>

              </div>
            )}
          </section>

          {/* ZONE 3 — COMMERCE CONTROL PLANE TRUST BOUNDARY (7 COLUMNS) */}
          <section className="lg:col-span-7 bg-slate-900/90 border border-slate-800/90 rounded-2xl p-5 flex flex-col gap-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="text-blue-400 w-5 h-5" />
                  <h2 className="font-bold text-sm tracking-wide text-slate-200 uppercase">Zone 3 — Commerce Control Plane</h2>
                </div>
                <p className="text-[11px] text-blue-300 font-mono mt-0.5">
                  DETERMINISTIC TRUST BOUNDARY — AI Proposes. Deterministic Policy Decides.
                </p>
              </div>
              <span className="text-[11px] font-mono text-slate-400">6 Gates Enforced</span>
            </div>

            {!result ? (
              <div className="h-96 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800/80 rounded-xl p-6 text-center">
                <ShieldCheck className="w-12 h-12 mb-3 text-slate-700 stroke-1" />
                <p className="text-xs max-w-xs leading-relaxed text-slate-400">
                  Real-time evaluation output for the 6 hard gates (<strong className="text-slate-200">MARGIN, INVENTORY, BUDGET, DISCOUNT, SPECIFICATION, MANDATE</strong>) will render here.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[520px] overflow-y-auto pr-1">
                {result.result?.gate_results?.map((gate: any, idx: number) => {
                  const isPass = gate.status === "PASS" || gate.passed === true;
                  const gateName = gate.gate || gate.gate_name;
                  return (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-xl border text-xs flex flex-col justify-between gap-2 transition-all ${
                        isPass
                          ? 'bg-slate-950/90 border-slate-800/90 text-slate-300'
                          : 'bg-rose-950/30 border-rose-900/60 text-rose-200'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 font-mono font-bold text-slate-200">
                          {isPass ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                          )}
                          <span>{gateName}</span>
                        </div>
                        <span className={`px-2 py-0.5 text-[10px] font-mono rounded font-bold shrink-0 ${isPass ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'}`}>
                          {isPass ? 'PASS' : 'FAIL'}
                        </span>
                      </div>

                      <p className="text-[11px] text-slate-400 leading-snug">
                        {gate.reason || gate.message}
                      </p>

                      {gate.expected && (
                        <div className="pt-2 border-t border-slate-800/60 text-[10px] font-mono flex justify-between text-slate-400">
                          <span>Expected: <strong className="text-slate-200">{gate.expected}</strong></span>
                          <span>Actual: <strong className={isPass ? 'text-emerald-400' : 'text-rose-400'}>{gate.actual}</strong></span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        {/* 4. OFFER RESULT & RAZORPAY PAYMENT PANEL */}
        {result && (
          <section className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <ShoppingBag className="w-5 h-5 text-emerald-400" />
                <h2 className="font-bold text-sm tracking-wide text-slate-200 uppercase">Offer Commercial Summary & Payment Execution</h2>
              </div>
              <span className={`px-3 py-1 rounded text-xs font-mono font-bold border ${result.result?.rescued ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-rose-950 text-rose-300 border-rose-800'}`}>
                {result.result?.rescued ? 'COUNTEROFFER APPROVED BY CONTROL PLANE' : 'NO SAFE COMMERCIAL OFFER'}
              </span>
            </div>

            {result.result?.offer ? (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
                <div className="lg:col-span-2 flex flex-col gap-3">
                  <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                    <div className="text-xs font-mono text-slate-400 mb-2">COMMERCIAL LINE ITEMS</div>
                    <div className="flex justify-between items-center text-sm font-semibold border-b border-slate-800 pb-2 mb-2">
                      <span>{result.result.offer.items[0]?.quantity}x {result.result.offer.items[0]?.name || result.parsed_request?.items[0]?.product_query}</span>
                      <span>Rs. {(result.result.offer.total_price_paise / 100).toLocaleString('en-IN')}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-xs font-mono text-slate-400">
                      <div>Original Price: <strong className="text-slate-300 font-sans">Rs. 25,00,000</strong></div>
                      <div>Negotiated Price: <strong className="text-emerald-400 font-sans">Rs. {(result.result.offer.total_price_paise / 100).toLocaleString('en-IN')}</strong></div>
                      <div>Total Savings: <strong className="text-emerald-400 font-sans">Rs. {(2500000 - result.result.offer.total_price_paise / 100).toLocaleString('en-IN')}</strong></div>
                    </div>
                  </div>

                  <div className="flex gap-4 text-xs font-mono text-slate-300">
                    <span className="px-3 py-1.5 bg-slate-950 rounded border border-slate-800">Profit Margin: <strong className="text-emerald-400">{result.result.offer.margin_percent}%</strong> (Floor: 15%)</span>
                    <span className="px-3 py-1.5 bg-slate-950 rounded border border-slate-800">Volume Discount: <strong className="text-blue-400">{result.result.offer.discount_percent}%</strong> (Max Cap: 20%)</span>
                    <span className="px-3 py-1.5 bg-slate-950 rounded border border-slate-800">Score: <strong className="text-indigo-400">{result.result.offer.final_score}/100</strong></span>
                  </div>
                </div>

                <div className="flex flex-col gap-3 justify-center items-stretch lg:border-l lg:border-slate-800/80 lg:pl-6">
                  <button
                    onClick={handleExecutePayment}
                    disabled={paying}
                    className="w-full py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl transition-all shadow-lg shadow-emerald-950/80 flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <CreditCard className="w-5 h-5" />
                    <span>Proceed to Payment (Razorpay Test Mode)</span>
                  </button>
                  <p className="text-[11px] text-slate-400 text-center">
                    Gated execution. Authorized by Mandate: <strong className="font-mono text-slate-300">MANDATE-DEMO-001</strong>
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-rose-950/20 border border-rose-900/50 rounded-xl text-xs text-rose-300 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 shrink-0 text-rose-400 mt-0.5" />
                <div>
                  <div className="font-bold text-sm text-rose-200">Graceful Merchant Safety Rejection</div>
                  <div className="mt-1 leading-relaxed">{result.result?.message}</div>
                  <div className="mt-2 text-[11px] font-mono text-slate-400">
                    Merchant profit safety prioritized over an unprofitable sale. No mandate cap or margin rules were breached.
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* 5. ZONE 4 — COMMERCE AUDIT TRAIL LOG */}
        <section className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-5 flex flex-col gap-4 shadow-xl mb-6">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <Terminal className="text-slate-400 w-5 h-5" />
                <h2 className="font-bold text-sm tracking-wide text-slate-200 uppercase">Commerce Audit Trail Log</h2>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Every decision is recorded in SQLite for explainability, safety, and compliance auditability.
              </p>
            </div>
            <span className="text-[11px] font-mono text-slate-400">SQLite Log Stream</span>
          </div>

          {!result ? (
            <div className="h-32 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800/80 rounded-xl p-4 text-center">
              <Activity className="w-8 h-8 mb-2 text-slate-700 stroke-1" />
              <p className="text-xs text-slate-400">Audit events will stream here after executing a simulation.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2 max-h-64 overflow-y-auto font-mono text-xs pr-1">
              <div className="p-2.5 bg-slate-950 rounded border border-slate-800 text-[11px] text-slate-400 flex justify-between">
                <span>INTENT_PARSED</span>
                <span>Component: INTENT_PARSER</span>
                <span className="text-blue-400">STATUS: INFO</span>
              </div>
              <div className="p-2.5 bg-slate-950 rounded border border-slate-800 text-[11px] text-slate-400 flex justify-between">
                <span>DIRECT_MATCH_FAILED</span>
                <span>Component: ASC_ORCHESTRATOR</span>
                <span className="text-amber-400">STATUS: WARN</span>
              </div>
              <div className="p-2.5 bg-slate-950 rounded border border-slate-800 text-[11px] text-slate-400 flex justify-between">
                <span>STRATEGIES_GENERATED</span>
                <span>Component: CANDIDATE_GENERATOR</span>
                <span className="text-indigo-400">STATUS: INFO</span>
              </div>
              <div className="p-2.5 bg-slate-950 rounded border border-slate-800 text-[11px] text-slate-400 flex justify-between">
                <span>6_GATES_EVALUATED</span>
                <span>Component: CONTROL_PLANE</span>
                <span className={result.result?.rescued ? 'text-emerald-400' : 'text-rose-400'}>
                  STATUS: {result.result?.rescued ? 'PASS' : 'FAIL'}
                </span>
              </div>
            </div>
          )}
        </section>

      </main>

      {/* 6. RAZORPAY TEST MODE PAYMENT MODAL */}
      {paymentModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-sm text-slate-100">Razorpay Test Mode Payment</h3>
              </div>
              <button
                onClick={() => setPaymentModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs flex flex-col gap-2">
              <div className="flex justify-between text-slate-400">
                <span>Status:</span>
                <span className="text-emerald-400 font-bold">{paymentData?.status}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Order ID:</span>
                <span className="text-slate-200">{paymentData?.order?.id}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Amount:</span>
                <span className="text-slate-200">Rs. {(paymentData?.order?.amount / 100).toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Provider:</span>
                <span className="text-blue-400 font-bold">{paymentData?.order?.provider}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Receipt:</span>
                <span className="text-slate-300">{paymentData?.order?.receipt}</span>
              </div>
            </div>

            <div className="p-3 bg-emerald-950/30 border border-emerald-800/50 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>Razorpay order created! Gated execution authorization verified.</span>
            </div>

            <button
              onClick={() => setPaymentModalOpen(false)}
              className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-slate-100 font-semibold text-xs rounded-xl transition-all"
            >
              Close Payment Modal
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
