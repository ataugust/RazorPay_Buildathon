"use client";

import React, { useState } from 'react';
import { ShieldCheck, Cpu, ArrowRight, Zap, CheckCircle2, AlertTriangle, AlertCircle, ShoppingBag } from 'lucide-react';

export default function Home() {
  const [prompt, setPrompt] = useState("Order 20 Lenovo IdeaPad laptops with a maximum budget of ₹25L.");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleRunDemo = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("http://localhost:8000/api/purchase/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Error connecting to ASC backend at http://localhost:8000");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen p-6 max-w-7xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <header className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-blue-500 w-8 h-8" />
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              ASC — Autonomous Sales Counterparty
            </h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Merchant-Side AI Commerce Engine & Deterministic Control Plane
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 bg-blue-950 border border-blue-800 text-blue-300 rounded-full text-xs font-mono">
            Track 01: Agentic Commerce
          </span>
          <span className="px-3 py-1 bg-emerald-950 border border-emerald-800 text-emerald-300 rounded-full text-xs font-mono flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Razorpay Test Mode
          </span>
        </div>
      </header>

      {/* Input Prompt Controls */}
      <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row gap-4 items-center">
        <div className="flex-1 w-full">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 block">
            Buyer Agent Prompt Intent
          </label>
          <input
            type="text"
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>
        <button
          onClick={handleRunDemo}
          disabled={loading}
          className="w-full md:w-auto px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-900/30 disabled:opacity-50"
        >
          {loading ? (
            <span>Executing Negotiation...</span>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              <span>Simulate A2A Transaction</span>
            </>
          )}
        </button>
      </section>

      {/* Dual Screen Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Screen: A2A Network & Buyer Intent */}
        <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="text-emerald-400 w-5 h-5" />
              <h2 className="font-semibold text-slate-200">A2A Negotiation Network</h2>
            </div>
            <span className="text-xs text-slate-400">Probabilistic Agent Reasoning</span>
          </div>

          {!result ? (
            <div className="h-96 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800 rounded-lg p-6 text-center">
              <ShoppingBag className="w-12 h-12 mb-3 text-slate-600 stroke-1" />
              <p className="text-sm">Click "Simulate A2A Transaction" to initiate buyer intent parsing and counteroffer reasoning.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
                <div className="text-xs font-mono text-blue-400 mb-1">BUYER REQUEST PARSED</div>
                <div className="text-sm font-semibold">{result.parsed_request?.items[0]?.quantity}x {result.parsed_request?.items[0]?.product_query}</div>
                <div className="text-xs text-slate-400 mt-1">Max Authorized Budget: ₹{(result.parsed_request?.max_budget_paise / 100).toLocaleString('en-IN')}</div>
              </div>

              <div className="flex justify-center my-1">
                <ArrowRight className="text-slate-600 rotate-90 w-5 h-5" />
              </div>

              <div className={`p-4 rounded-lg border ${result.result?.rescued ? 'bg-emerald-950/40 border-emerald-800' : 'bg-slate-950 border-slate-800'}`}>
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-emerald-400">MERCHANT ASC COUNTEROFFER</span>
                  {result.result?.rescued && (
                    <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 text-[10px] rounded border border-emerald-500/40">
                      RESCUED DEAL
                    </span>
                  )}
                </div>
                {result.result?.offer ? (
                  <div>
                    <div className="text-sm font-semibold text-slate-200">{result.result.offer.explanation}</div>
                    <div className="text-xs text-slate-400 mt-2 font-mono">
                      Offer Total: ₹{(result.result.offer.total_price_paise / 100).toLocaleString('en-IN')} | Profit Margin: {result.result.offer.margin_percent}%
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-amber-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{result.result?.message}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Right Screen: Control Plane Audit Trail */}
        <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="text-blue-400 w-5 h-5" />
              <h2 className="font-semibold text-slate-200">Commerce Control Plane Audit Trail</h2>
            </div>
            <span className="text-xs text-slate-400">Deterministic Trust Boundary</span>
          </div>

          {!result ? (
            <div className="h-96 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800 rounded-lg p-6 text-center">
              <ShieldCheck className="w-12 h-12 mb-3 text-slate-600 stroke-1" />
              <p className="text-sm">Gate checks (BudgetGate, MarginGate, InventoryGate, PolicyGate, MandateGate) will display here in real-time.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-3 max-h-96 overflow-y-auto pr-1">
              <div className="p-3 bg-slate-950 rounded border border-blue-900/40 text-xs font-mono flex items-center justify-between">
                <span className="text-blue-400">TRUST BOUNDARY: PROPOSAL EVALUATION</span>
                <span className="text-slate-400">{result.result?.transaction_id}</span>
              </div>

              {result.result?.gate_results?.map((gate: any, idx: number) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border text-xs flex items-start justify-between gap-3 ${
                    gate.passed
                      ? 'bg-slate-950/80 border-slate-800 text-slate-300'
                      : 'bg-rose-950/20 border-rose-900/50 text-rose-300'
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    {gate.passed ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <div className="font-mono font-semibold text-slate-200">{gate.gate_name}</div>
                      <div className="mt-0.5 text-slate-400">{gate.message}</div>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 text-[10px] font-mono rounded ${gate.passed ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'}`}>
                    {gate.passed ? 'PASS' : 'FAIL'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
