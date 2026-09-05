"use client";
import {useEffect,useState} from "react";
import {money} from "../lib/format";
type Incoming = {id:string;state:string;transaction_id:string|null;requirements:{product_query:string;quantity:number;max_budget_paise:number|null;hard_specs:Record<string,string|number|null>}};
export function MerchantInbox() {
  const [requests,setRequests]=useState<Incoming[]>([]);
  useEffect(()=>{let alive=true; const refresh=()=>fetch("/backend-api/api/merchant-inbox").then(r=>r.ok?r.json():null).then(data=>{if(alive && data)setRequests(data.requests);}).catch(()=>{});refresh();const timer=setInterval(refresh,1500);return()=>{alive=false;clearInterval(timer);};},[]);
  if(!requests.length)return null;
  return <details className="mx-auto my-4 max-w-6xl rounded-xl border border-indigo-100 bg-white p-4" open={requests.some(r=>r.state==="WAITING")}><summary className="cursor-pointer text-sm font-semibold text-indigo-700">Buyer requests received · {requests.length}</summary><div className="mt-3 grid gap-3 sm:grid-cols-2">{requests.slice().reverse().slice(0,6).map(r=><div key={r.id} className="rounded-lg bg-slate-50 p-3 text-sm"><p className="font-semibold">{r.requirements.quantity} × {r.requirements.product_query}</p><p className="mt-1 text-slate-500">Budget: {money(r.requirements.max_budget_paise)} · {r.state==="WAITING"?"Evaluating inventory":r.state==="COMPLETED"?"Purchase approved":"Response sent"}</p><p className="mt-1 text-xs text-slate-500">{Object.entries(r.requirements.hard_specs||{}).filter(([,v])=>v!==null).map(([k,v])=>`${k.replaceAll("_"," ")}: ${v}`).join(" · ")}</p>{r.transaction_id && <p className="mt-1 font-mono text-xs text-indigo-500">{r.transaction_id}</p>}</div>)}</div></details>;
}
