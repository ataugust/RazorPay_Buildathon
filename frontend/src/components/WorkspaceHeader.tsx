"use client";
import { Building2, ShieldCheck, ShoppingBag } from "lucide-react";
export function WorkspaceHeader({workspace, online}: {workspace:"buyer"|"merchant"; online:boolean; agentLabel?:string}) {
  const Icon = workspace === "buyer" ? ShoppingBag : Building2;
  return <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur"><div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-5 sm:px-8"><div className="flex items-center gap-3"><span className="rounded-xl bg-indigo-600 p-2 text-white"><ShieldCheck className="h-5 w-5"/></span><strong>ASC</strong><span className="hidden text-sm text-slate-400 sm:inline">Autonomous Sales Counterparty</span></div><div className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-semibold"><Icon className="h-4 w-4"/>{workspace === "buyer" ? "Buyer Workspace":"Merchant Console"}</div><span className="hidden text-xs text-slate-500 md:block">{online ? "Connected":"Connecting…"}</span></div></header>;
}
