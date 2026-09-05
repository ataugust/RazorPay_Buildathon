"use client";
import { useEffect, useState } from "react";
import { MerchantApp } from "./MerchantApp";
import { Button, Card, ErrorState } from "./ui/DesignSystem";
export function MerchantAccess() {
  const [authenticated, setAuthenticated] = useState(false);
  const [password,setPassword] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState<string|null>(null);
  useEffect(()=>{fetch("/backend-api/api/merchant-session").then(r=>r.json()).then(r=>setAuthenticated(r.authenticated)).catch(()=>setError("Unable to connect to the server."));},[]);
  const login = async () => {
    setBusy(true); setError(null);
    try {const r=await fetch("/backend-api/api/merchant-session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password})}); const data=await r.json(); if(!r.ok) throw new Error(data.detail); setAuthenticated(true); setPassword("");}
    catch(e){setError((e as Error).message);} finally{setBusy(false);}
  };
  if(authenticated) return <><MerchantApp/><button className="fixed bottom-3 right-4 z-50 rounded-lg border bg-white px-3 py-2 text-xs text-slate-600" onClick={async()=>{await fetch("/backend-api/api/merchant-session",{method:"DELETE"});setAuthenticated(false);}}>Sign out</button></>;
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6"><Card className="w-full max-w-md p-8"><h1 className="text-2xl font-semibold">Merchant Console</h1><p className="mt-2 text-sm text-slate-500">Sign in to manage inventory, proposals, and merchant policies.</p><form onSubmit={e=>{e.preventDefault();login();}}><label className="mt-6 block text-sm font-medium">Merchant passcode<input type="password" value={password} autoComplete="current-password" onChange={e=>setPassword(e.target.value)} className="mt-2 h-11 w-full rounded-lg border px-3"/></label>{error && <div className="mt-4"><ErrorState message={error}/></div>}<Button loading={busy} disabled={!password} className="mt-5 w-full">Sign in</Button></form></Card></main>;
}
