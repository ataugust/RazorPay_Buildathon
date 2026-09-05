"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { ClarificationRequest, Deal } from "../types/commerce";
import { BuyerWorkspace } from "./BuyerWorkspace";
import { WorkspaceHeader } from "./WorkspaceHeader";

export function BuyerApp() {
  const [activeDeal, setActiveDeal] = useState<Deal | null>(null);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [online, setOnline] = useState(false);
  const [agentLabel, setAgentLabel] = useState("Loading…");
  const activeRef = useRef<Deal | null>(null);
  useEffect(() => { activeRef.current = activeDeal; }, [activeDeal]);

  const refresh = useCallback(async () => {
    try {
      const [health, dealData] = await Promise.all([api.health(), api.listDeals()]);
      setOnline(health.status === "healthy"); setDeals(dealData.deals);
      setAgentLabel(health.agent_provider === "gemini" ? (health.agent_model || "Gemini Flash") : "Deterministic fallback");
      if (activeRef.current) setActiveDeal(await api.getDeal(activeRef.current.transaction_id));
      setError(null);
    } catch (cause) { setOnline(false); setError(cause instanceof Error ? cause.message : "ASC API is unavailable"); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { const timer = window.setInterval(refresh, 2500); return () => window.clearInterval(timer); }, [refresh]);

  const createDeal = async (prompt: string): Promise<ClarificationRequest | null> => {
    if (busy) return null;
    setBusy(true); setError(null);
    try {
      const response = await api.createDeal(prompt);
      if ("requires_clarification" in response) return response;
      setActiveDeal(response); setDeals((current) => [response, ...current.filter((item) => item.transaction_id !== response.transaction_id)]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create the deal"); }
    finally { setBusy(false); }
    return null;
  };
  const rejectDeal = async (reason?: string) => {
    if (!activeDeal || busy) return;
    setBusy(true); setError(null);
    try { const deal = await api.rejectDeal(activeDeal.transaction_id, reason); setActiveDeal(deal); setDeals((current) => current.map((item) => item.transaction_id === deal.transaction_id ? deal : item)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not reject this offer"); }
    finally { setBusy(false); }
  };
  const acceptDeal = async () => {
    if (!activeDeal || busy) return;
    setBusy(true); setError(null);
    try { const response = await api.acceptDeal(activeDeal.transaction_id); setActiveDeal(response.deal); setDeals((current) => current.map((item) => item.transaction_id === response.deal.transaction_id ? response.deal : item)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not complete this purchase"); }
    finally { setBusy(false); }
  };
  const openDeal = async (id: string) => {
    setBusy(true); setError(null);
    try { setActiveDeal(await api.getDeal(id)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load this purchase"); }
    finally { setBusy(false); }
  };
  return <div className="min-h-screen bg-slate-50 text-slate-900"><WorkspaceHeader workspace="buyer" online={online} agentLabel={agentLabel} /><BuyerWorkspace deal={activeDeal} deals={deals} busy={busy} error={error} onCreate={createDeal} onReject={rejectDeal} onAccept={acceptDeal} onOpenDeal={openDeal} onReset={() => { setActiveDeal(null); setError(null); }} /></div>;
}
