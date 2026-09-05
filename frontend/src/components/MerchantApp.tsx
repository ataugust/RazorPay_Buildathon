"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { Analytics, AuditEvent, Deal, MerchantPolicy, Product } from "../types/commerce";
import { MerchantConsole, MerchantPage } from "./MerchantConsole";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { MerchantInbox } from "./MerchantInbox";

export function MerchantApp() {
  const [page, setPage] = useState<MerchantPage>("dashboard");
  const [deals, setDeals] = useState<Deal[]>([]);
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [catalog, setCatalog] = useState<Product[]>([]);
  const [policy, setPolicy] = useState<MerchantPolicy | null>(null);
  const [activity, setActivity] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [online, setOnline] = useState(false);
  const [agentLabel, setAgentLabel] = useState("Loading…");
  const selectedRef = useRef<Deal | null>(null);
  useEffect(() => { selectedRef.current = selectedDeal; }, [selectedDeal]);
  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [health, dealData, analyticsData, catalogData, policyData, activityData] = await Promise.all([api.health(), api.listDeals(), api.analytics(), api.catalog(), api.policy(), api.activity()]);
      setOnline(health.status === "healthy"); setDeals(dealData.deals); setAnalytics(analyticsData); setCatalog(catalogData.products); setPolicy(policyData); setActivity(activityData.events);
      setAgentLabel(health.agent_provider === "gemini" ? (health.agent_model || "Gemini Flash") : "Deterministic fallback");
      if (selectedRef.current) setSelectedDeal(await api.getDeal(selectedRef.current.transaction_id));
      setError(null);
    } catch (cause) { setOnline(false); setError(cause instanceof Error ? cause.message : "ASC API is unavailable"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { const timer = window.setInterval(() => refresh(true), 2500); return () => window.clearInterval(timer); }, [refresh]);
  const selectDeal = async (id: string) => { if (!id) { setSelectedDeal(null); return; } try { setSelectedDeal(await api.getDeal(id)); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load deal"); } };
  const updatePolicy = async (value: Partial<MerchantPolicy>) => { try { setPolicy(await api.updatePolicy(value)); setError(null); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update policy"); } };
  return <div className="min-h-screen bg-slate-50 text-slate-900"><WorkspaceHeader workspace="merchant" online={online} agentLabel={agentLabel} /><MerchantInbox /><MerchantConsole page={page} onPage={(next) => { setPage(next); if (next !== "deals") setSelectedDeal(null); }} deals={deals} selectedDeal={selectedDeal} onSelectDeal={selectDeal} analytics={analytics} catalog={catalog} policy={policy} activity={activity} loading={loading} error={error} onRefresh={() => refresh()} onUpdatePolicy={updatePolicy} /></div>;
}
